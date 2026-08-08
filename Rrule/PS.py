#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[PS] 活塞 (Piston): 雷表示石头, 非雷格表示空气, 题板外为空气. 线索格表示把该格变成一个箭头方向的活塞, 试图展开, 
若有题板内的非雷格被方块填充则变为同方向的活塞并尝试激活. 线索数字表示所有方块被b36化的总次数.
"""

from typing import List, Dict, Tuple, Union, Optional, cast
import random

from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.board import Board, Position, JSONObject
from minesweepervariants.json_object import deep_unwrap, ImmutableDict
from minesweepervariants.utils.tool import get_random, get_logger
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue
from minesweepervariants.utils.image_template import get_col, get_row, get_text, get_dummy, get_image
from minesweepervariants.utils.web_template import Number


def to_base36(n: int) -> str:
    """将整数转换为 base36 字符串 (0-9A-Z)"""
    if n == 0:
        return "0"
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    result = []
    while n > 0:
        result.append(chars[n % 36])
        n //= 36
    return "".join(reversed(result))


def from_base36(s: str) -> int:
    """将 base36 字符串转换为整数"""
    return int(s, 36)


class ValuePS(AbstractClueValue):
    """线索值类：包含方向和数字，数字以 base36 字符串显示"""
    id = "PS"

    # 方向常量
    UP = 0
    RIGHT = 1
    DOWN = 2
    LEFT = 3
    DIR_NAMES = ["up", "right", "down", "left"]
    DIR_SYMBOLS = ["↑", "→", "↓", "←"]

    def __init__(
        self,
        pos: Position,
        direction: int,
        count: int,
        code: Optional[bytes] = None
    ):
        super().__init__(pos, code or b'')
        self.pos = pos
        self.direction = direction
        self.count = count
        self.value = SingleIntValue(count)

    def __repr__(self) -> str:
        """显示为 base36 编码的数字，例如 10 -> A"""
        return to_base36(self.count)

    @classmethod
    def from_json(cls, pos: Position, data: JSONObject) -> 'AbstractValue':
        # data 可能是一个 ImmutableDict，直接读取其中的字段
        # 兼容两种格式：
        # 1. 带有 _SingleIntValue 标记的模板格式
        # 2. 直接包含 data 和 direction 的字典格式
        _data = deep_unwrap(data)
        # 如果是模板格式
        if isinstance(_data, dict) and "_SingleIntValue" in _data:
            count = _data.get("data", 0)
            direction = _data.get("direction", cls.UP)
            return cls(pos, direction, count)
        # 如果是直接格式
        if isinstance(_data, dict):
            count = _data.get("data", 0)
            direction = _data.get("direction", cls.UP)
            return cls(pos, direction, count)
        # 如果是旧格式（SingleIntValue 的直接数据）
        if isinstance(_data, int):
            return cls(pos, cls.UP, _data)
        raise TypeError(f"Invalid data for PS clue: {_data}")

    def json(self) -> JSONObject:
        return ImmutableDict({
            "_SingleIntValue": True,
            "data": self.count,
            "direction": self.direction,
        })

    def code(self) -> bytes:
        return bytes([self.direction, self.count])

    @classmethod
    def type(cls) -> bytes:
        return cls.id.encode("ascii")

    def tag(self, board: Board) -> bytes:
        """角标显示方向"""
        return self.DIR_SYMBOLS[self.direction].encode("ascii")

    def compose(self, board: Board) -> Dict:
        """渲染：方向箭头 + 数字"""
        # 显示数字（base36）和方向箭头
        num_text = self.__repr__()
        arrow = self.DIR_SYMBOLS[self.direction]
        # 如果是上下方向，垂直排列；左右方向水平排列
        if self.direction in (self.UP, self.DOWN):
            return get_col(
                get_dummy(height=0.1),
                get_text(arrow, color=("#FFFFFF", "#000000")),
                get_dummy(height=0.05),
                get_text(num_text, color=("#FFFFFF", "#000000")),
                get_dummy(height=0.1),
            )
        else:
            return get_row(
                get_dummy(width=0.1),
                get_text(arrow, color=("#FFFFFF", "#000000")),
                get_dummy(width=0.05),
                get_text(num_text, color=("#FFFFFF", "#000000")),
                get_dummy(width=0.1),
            )

    def web_component(self, board: Board) -> Dict:
        """网页渲染"""
        return Number(self.__repr__())

    def high_light(self, board: Board) -> List[Position]:
        """高亮显示该活塞传播路径上的所有格子"""
        positions = []
        cur = self.pos
        # 沿方向前进，直到遇到雷或边界
        while True:
            positions.append(cur)
            # 根据方向移动
            if self.direction == self.UP:
                cur = cur.up()
            elif self.direction == self.DOWN:
                cur = cur.down()
            elif self.direction == self.LEFT:
                cur = cur.left()
            elif self.direction == self.RIGHT:
                cur = cur.right()
            else:
                break
            if not board.in_bounds(cur) or board.get_type(cur, special='raw') == "F":
                break
        return positions

    def create_constraints(self, board: Board, switch):
        """创建约束：该线索值等于从该格沿方向连续非雷格的数量"""
        model = board.get_model()
        s = switch.get(model, self)

        # 沿方向收集格子
        positions = []
        cur = self.pos
        while True:
            # 移动
            if self.direction == self.UP:
                cur = cur.up()
            elif self.direction == self.DOWN:
                cur = cur.down()
            elif self.direction == self.LEFT:
                cur = cur.left()
            elif self.direction == self.RIGHT:
                cur = cur.right()
            else:
                break
            if not board.in_bounds(cur):
                break
            # 如果遇到雷，停止（雷不计数）
            if board.get_type(cur, special='raw') == "F":
                break
            positions.append(cur)

        # 如果没有位置，则线索值应为1（只包含自身）
        if not positions:
            model.Add(self.count == 1).OnlyEnforceIf(s)
            return

        # 创建变量：每个位置是否是连续的活塞链的一部分
        # 定义：位置 i 是链的一部分当且仅当该位置是非雷
        # 并且所有前面的位置也都是非雷
        chain_vars = []
        prev_cont = None
        for i, pos in enumerate(positions):
            mine_var = board.get_variable(pos, special='raw')
            # 如果当前位置是雷，则链在此处中断
            is_mine = model.NewBoolVar(f"ps_is_mine_{pos}")
            model.Add(is_mine == mine_var)

            # 当前格是链的一部分：当前格非雷 且 前面所有格非雷（即前一个格是链的一部分）
            cont = model.NewBoolVar(f"ps_cont_{pos}")
            if i == 0:
                # 第一个格：只要非雷即为链的一部分
                model.Add(cont == 1 - mine_var).OnlyEnforceIf(s)
            else:
                # 后续格：前一个格是链的一部分 且 当前格非雷
                model.Add(cont == 1).OnlyEnforceIf([prev_cont, mine_var.Not(), s])
                model.Add(cont == 0).OnlyEnforceIf([prev_cont.Not(), s])
                model.Add(cont == 0).OnlyEnforceIf([mine_var, s])
            chain_vars.append(cont)
            prev_cont = cont

        # 线索值 = 1（自身） + 链中格子的数量
        total_count = 1 + sum(chain_vars)
        model.Add(total_count == self.count).OnlyEnforceIf(s)


class RulePS(AbstractClueRule):
    """活塞规则：每个非雷格显示一个箭头方向和一个base36数字，数字表示沿该方向连续非雷格的数量"""
    id = "PS"
    name = "Piston"
    name.zh_CN = "活塞"
    doc = (
        "Mines are stone, non-mine cells are air, outside board is air. "
        "A clue cell becomes a piston pointing in an arrow direction. "
        "The piston tries to extend, and if it encounters a non-mine cell, that cell becomes a piston pointing in the same direction and tries to activate. "
        "The clue number is the total number of blocks converted, expressed in base36."
    )
    doc.zh_CN = (
        "雷表示石头, 非雷格表示空气, 题板外为空气. "
        "线索格表示把该格变成一个箭头方向的活塞, 试图展开, "
        "若有题板内的非雷格被方块填充则变为同方向的活塞并尝试激活. "
        "线索数字表示所有方块被b36化的总次数."
    )
    tags = ["Creative", "Local", "Arrow Clue", "Number Clue", "Construction"]
    creation_time = "2026-07-07"
    author = ("NT", 2201963934)

    def __init__(self, board: Board = None, data: Optional[str] = None):
        super().__init__(board, data)
        # 如果 data 指定，可以用于固定方向或随机种子
        self.seed = None
        if data:
            try:
                self.seed = int(data)
            except ValueError:
                pass

    def fill(self, board: Board) -> Board:
        """为所有非雷格分配活塞线索"""
        rng = get_random() if self.seed is None else random.Random(self.seed)
        # 收集所有非雷格
        for pos, _ in board("N", special='raw'):
            # 随机选择一个方向
            direction = rng.randint(0, 3)  # UP, RIGHT, DOWN, LEFT
            # 计算沿该方向连续非雷格的数量（包括自身）
            count = self._count_extension(board, pos, direction)
            # 创建线索对象
            value = ValuePS(pos, direction, count)
            board.set_value(pos, value)
        return board

    def _count_extension(self, board: Board, pos: Position, direction: int) -> int:
        """计算从 pos 出发沿 direction 方向连续非雷格的数量（包括 pos 自身）"""
        count = 1  # 包含自身
        cur = pos
        while True:
            # 移动
            if direction == ValuePS.UP:
                cur = cur.up()
            elif direction == ValuePS.DOWN:
                cur = cur.down()
            elif direction == ValuePS.LEFT:
                cur = cur.left()
            elif direction == ValuePS.RIGHT:
                cur = cur.right()
            else:
                break
            if not board.in_bounds(cur):
                break
            if board.get_type(cur, special='raw') == "F":
                break
            count += 1
        return count

    def create_constraints(self, board: Board, switch):
        """PS 规则本身不需要额外的全局约束，线索对象的约束已覆盖"""
        pass

    def init_clear(self, board: Board):
        """可选：清除阶段无需特殊处理"""
        pass
