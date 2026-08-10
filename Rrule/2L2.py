#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/08/10
# @Author  : Gat (992600401)
# @FileName: 2L2.py
"""
[2L2] 每行每列恰有两个误差线索，误差线索比实际值大1或小1
作者: Gat (992600401)
最后编辑时间: 2026-08-10

实现说明：
- 使用副板标记误差位置（VALUE_CIRCLE 表示误差，VALUE_CROSS 表示非误差）
- fill 阶段：随机选择每行每列各两个位置作为误差标记，并生成对应的显示值
- create_constraints 阶段：
  1. 副板每行每列恰好两个 CIRCLE
  2. 线索格若为误差（对应副板为 CIRCLE），则真实值 = 显示值 ± 1
  3. 线索格若非误差（对应副板为 CROSS），则真实值 = 显示值
"""

from typing import Self
from collections import defaultdict

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position, Size
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import JSONObject, deep_unwrap
from minesweepervariants.utils.impl_obj import VALUE_CIRCLE, VALUE_CROSS
from minesweepervariants.utils.tool import get_logger, get_random
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template

NAME_2L2 = "2L2"


def generate_error_positions(n: int) -> list[tuple[int, int]]:
    """
    生成每行每列恰好两个误差标记的位置。
    使用两阶段方法：
    1. 为每一行随机选择两个不同的列
    2. 验证每列是否恰好被选中两次
    3. 如果不满足，重新生成
    """
    random = get_random()
    max_attempts = 10000
    
    for _ in range(max_attempts):
        # 为每一行选择两个不同的列
        row_cols = []
        for _ in range(n):
            cols = list(range(n))
            random.shuffle(cols)
            row_cols.append((cols[0], cols[1]))
        
        # 统计每列被选中的次数
        col_counts = [0] * n
        for c1, c2 in row_cols:
            col_counts[c1] += 1
            col_counts[c2] += 1
        
        # 检查是否每列恰好被选中两次
        if all(count == 2 for count in col_counts):
            result = []
            for row, (c1, c2) in enumerate(row_cols):
                result.append((row, c1))
                result.append((row, c2))
            return result
    
    # 如果多次尝试失败，使用确定性方法
    result = []
    for i in range(n):
        result.append((i, i))
        result.append((i, (i + n // 2) % n))
    return result


class Rule2L2(AbstractClueRule):
    """[2L2] 每行每列恰有两个误差线索"""

    id = "2L2"
    name = "Liar x2"
    name.zh_CN = "双误差"
    doc = "Each row and column has exactly two error clues. Error clues are 1 greater or 1 less than the true value."
    doc.zh_CN = "每行每列恰有两个误差线索。误差线索比真实值大1或小1。"
    tags = ["Variant", "Local", "Number Clue", "Extensive Trial", "Cryptic"]
    creation_time = "2026-08-10"
    author = ("Gat", 992600401)

    def __init__(self, board: "Board | None" = None, data: str | None = None) -> None:
        super().__init__(board, data)
        if board is None:
            return
        # 验证所有交互板尺寸一致且为正方形
        bound = board.boundary()
        if bound.row != bound.col:
            raise ValueError("2L2 要求正方形题板")
        for key in board.get_interactive_keys():
            _bound = board.boundary(key)
            if _bound.row != bound.row or _bound.col != bound.col:
                raise ValueError("所有交互题板尺寸必须一致")

        # 生成副板
        size = Size(bound.row + 1, bound.col + 1)
        board.generate_board(NAME_2L2, size)
        board.set_config(NAME_2L2, "pos_label", True)

    def fill(self, board: 'Board') -> 'Board':
        """填充所有线索格，并为副板设置误差标记"""
        self.init_clear(board)
        random = get_random()
        bound = board.boundary()
        n = bound.row + 1
        logger = get_logger()

        # 生成每行每列恰好两个误差标记的位置
        pos_map = generate_error_positions(n)
        pos_set = set(pos_map)

        # 在副板上标记误差位置（VALUE_CIRCLE）和非误差位置（VALUE_CROSS）
        for pos, _ in board(key=NAME_2L2):
            if (pos.row, pos.col) in pos_set:
                board.set_value(pos, VALUE_CIRCLE)
                logger.debug(f"[2L2] put O at {pos}")
            else:
                board.set_value(pos, VALUE_CROSS)
                logger.debug(f"[2L2] put X at {pos}")

        # 为每个非雷格计算真实值并生成线索
        for pos, _ in board("N", special='raw'):
            true_value = board.batch(pos.neighbors(2), mode="type").count("F")
            # 判断是否为误差位置（副板对应位置为 CIRCLE）
            is_error = (board.get_value(
                board.get_pos(pos.row, pos.col, NAME_2L2)
            ) == VALUE_CIRCLE)

            if is_error:
                # 误差：真实值 ± 1，但必须在 0..8 之间
                candidates = [true_value - 1, true_value + 1]
                candidates = [v for v in candidates if 0 <= v <= 8]
                if not candidates:
                    display_value = true_value
                else:
                    display_value = random.choice(candidates)
            else:
                display_value = true_value

            obj = Value2L2(pos, code=bytes([display_value]))
            board.set_value(pos, obj)
            logger.debug(f"[2L2] put {obj} to {pos}")

        return board

    def init_clear(self, board: 'Board') -> None:
        """清空副板上的标记"""
        for pos, _ in board(key=NAME_2L2):
            board.set_value(pos, None)

    def create_constraints(self, board: 'Board', switch: Switch) -> None:
        """创建约束：每行每列恰好两个误差标记，且线索值与真实值关系正确"""
        model = board.get_model()
        s = switch.get(model, self)

        bound = board.boundary(key=NAME_2L2)

        # 行约束：每行恰好两个标记为 CIRCLE（即误差）
        for pos in board.get_row_pos(bound):
            line = board.get_col_pos(pos)
            line_vars = board.batch(line, mode="variable", drop_none=True)
            model.Add(sum(line_vars) == 2).OnlyEnforceIf(s)

        # 列约束：每列恰好两个标记为 CIRCLE
        for pos in board.get_col_pos(bound):
            line = board.get_row_pos(pos)
            line_vars = board.batch(line, mode="variable", drop_none=True)
            model.Add(sum(line_vars) == 2).OnlyEnforceIf(s)


class Value2L2(AbstractClueValue):
    """2L2 线索值类，存储显示值，并约束真实值等于显示值（非误差）或显示值±1（误差）"""

    id = Rule2L2.id

    def __init__(self, pos: Position, code: bytes | None = None):
        super().__init__(pos, code or b'')
        self.pos = pos
        self.display_value = code[0] if code else 0
        self.value = SingleIntValue(self.display_value)

    @classmethod
    def from_json(cls, pos: Position, data: JSONObject) -> Self:
        _data = deep_unwrap(data)
        if not is_value_template(_data):
            raise TypeError("value is not template")
        single = SingleIntValue.try_from(_data)
        if single is None:
            raise ValueError("Invalid value template for 2L2")
        return cls(pos, bytes([single.value]))

    def __repr__(self) -> str:
        return str(self.display_value)

    def high_light(self, board: 'Board') -> list[Position]:
        """高亮周围八格（用于前端显示）"""
        return self.pos.neighbors(2)

    def create_constraints(self, board: 'Board', switch: Switch) -> None:
        """约束：真实雷数 = 显示值（非误差） 或 显示值 ± 1（误差）"""
        model = board.get_model()
        s = switch.get(model, self)

        # 获取当前线索的误差标记（副板对应位置）
        marker_pos = board.get_pos(self.pos.row, self.pos.col, NAME_2L2)
        marker_var = board.get_variable(marker_pos)
        if marker_var is None:
            return

        # 周围八格雷数（真实值）
        neighbor_vars = board.batch(self.pos.neighbors(2), mode="variable", drop_none=True)
        true_sum = sum(neighbor_vars) if neighbor_vars else 0

        # 情况1：非误差（marker_var == 0） -> 真实值 == 显示值
        model.Add(true_sum == self.display_value).OnlyEnforceIf([marker_var.Not(), s])

        # 情况2：误差（marker_var == 1） -> 真实值 == 显示值 + 1 或 显示值 - 1
        tmp_plus = model.NewBoolVar("tmp_plus")
        tmp_minus = model.NewBoolVar("tmp_minus")
        model.Add(true_sum == self.display_value + 1).OnlyEnforceIf([tmp_plus, s])
        model.Add(true_sum == self.display_value - 1).OnlyEnforceIf([tmp_minus, s])
        model.AddBoolOr([tmp_plus, tmp_minus]).OnlyEnforceIf([marker_var, s])
