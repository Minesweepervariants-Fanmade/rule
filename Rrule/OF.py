#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/08/09 03:06
# @Author  : NT (2201963934)
# @FileName: OF.py
"""
[OF] 偏移：线索表示其坐标偏移(x,y)格后周围八格中的雷数。
全题版共享x和y，x和y在2*n大小的副板上表示。
偏移时跨板，邻居格不跨版。
"""

from typing import TYPE_CHECKING, Dict, List, Optional, Self

from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, MASTER_BOARD_KEY
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import JSONObject
from minesweepervariants.size import Size
from minesweepervariants.utils.image_template import Element
from minesweepervariants.utils.impl_obj import VALUE_CIRCLE, VALUE_CROSS
from minesweepervariants.utils.tool import get_logger, get_random
from minesweepervariants.utils.value_template import SingleIntValue, Template

if TYPE_CHECKING:
    from minesweepervariants.position import Position

NAME_OFFSET = "OF_OFFSET"
logger = get_logger()


class RuleOF(AbstractClueRule):
    """[OF] 偏移规则类"""

    id = "OF"
    name = "Offset"
    name.zh_CN = "偏移"
    doc = "Clue shows the number of mines in the 8 cells around the position offset by (x,y). x and y are shared across the board and represented on a 2*n sub-board."
    doc.zh_CN = "线索表示其坐标偏移(x,y)格后周围八格中的雷数。全题版共享x和y，x和y在2*n大小的副板上表示。偏移时跨板，邻居格不跨版。"
    author = ("NT", 2201963934)
    tags = ["Creative", "Local", "Number Clue", "Aux Board", "Mine-Position"]
    creation_time = "2026-08-09"

    def __init__(self, board: Optional["Board"] = None, data: Optional[str] = None) -> None:
        super().__init__(board, data)
        if board is None:
            return

        # 获取主板尺寸（假设为正方形）
        bound = board.boundary(MASTER_BOARD_KEY)
        self.size = bound.row + 1
        if bound.row != bound.col:
            raise ValueError("OF 规则要求正方形题板")

        # 创建副板：2 行 × size 列
        # 第0行表示 x 偏移，第1行表示 y 偏移
        board.generate_board(NAME_OFFSET, Size(self.size, 2))
        board.set_config(NAME_OFFSET, "pos_label", True)
        board.set_config(NAME_OFFSET, "row_col", True)

    def fill(self, board: "Board") -> "Board":
        """填充副板标记和所有线索格的值"""
        self._init_clear(board)

        random = get_random()
        size = self.size

        # 随机选择 x 和 y 偏移值
        x_val = random.randint(0, size - 1)
        y_val = random.randint(0, size - 1)

        # 在副板上标记 x 和 y
        pos_x = board.get_pos(0, x_val, NAME_OFFSET)   # 第0行第x_val列
        pos_y = board.get_pos(1, y_val, NAME_OFFSET)   # 第1行第y_val列
        board.set_value(pos_x, VALUE_CIRCLE)
        board.set_value(pos_y, VALUE_CIRCLE)

        # 副板其他位置标记为 CROSS
        for pos, _ in board("N", key=NAME_OFFSET):
            board.set_value(pos, VALUE_CROSS)

        logger.debug(f"[OF] fill: x={x_val}, y={y_val}")

        # 为每个非雷格（线索格）计算偏移后的值
        for pos, _ in board("N", special="raw", key=MASTER_BOARD_KEY):
            # 偏移后位置（跨板：环绕）
            new_row = (pos.row + x_val) % size
            new_col = (pos.col + y_val) % size
            new_pos = board.get_pos(new_row, new_col, MASTER_BOARD_KEY)

            # 计算周围八格的雷数（不跨版）
            neighbor_count = self._count_mines_around(board, new_pos)

            # 创建线索值对象
            board.set_value(pos, ValueOF(pos, count=neighbor_count, x_val=x_val, y_val=y_val))

        return board

    def _count_mines_around(self, board: "Board", pos: "Position") -> int:
        """计算 pos 周围八格（同一子板内）的雷数"""
        if not board.in_bounds(pos):
            return 0
        neighbors = pos.neighbors(2)
        total = 0
        for n in neighbors:
            if board.in_bounds(n) and board.get_type(n, special="raw") == "F":
                total += 1
        return total

    def _init_clear(self, board: "Board") -> None:
        """清除副板上的所有标记"""
        for pos, _ in board(key=NAME_OFFSET):
            board.set_value(pos, None)

    def create_constraints(self, board: "Board", switch: "Switch") -> None:
        """创建 CP-SAT 约束"""
        model = board.get_model()
        s = switch.get(model, self)

        size = self.size

        # ---------- 1. 获取副板变量 ----------
        # 第0行：x 偏移标记
        x_vars = []
        for col in range(size):
            pos = board.get_pos(0, col, NAME_OFFSET)
            var = board.get_variable(pos)
            if var is None:
                raise ValueError(f"副板变量缺失: {pos}")
            x_vars.append(var)

        # 第1行：y 偏移标记
        y_vars = []
        for col in range(size):
            pos = board.get_pos(1, col, NAME_OFFSET)
            var = board.get_variable(pos)
            if var is None:
                raise ValueError(f"副板变量缺失: {pos}")
            y_vars.append(var)

        # ---------- 2. 约束每行恰好一个标记 ----------
        model.Add(sum(x_vars) == 1).OnlyEnforceIf(s)
        model.Add(sum(y_vars) == 1).OnlyEnforceIf(s)

        # ---------- 3. 创建 x_var 和 y_var 变量 ----------
        # x_var = 第0行中标记点的列索引
        x_var = model.NewIntVar(0, size - 1, "of_x_offset")
        y_var = model.NewIntVar(0, size - 1, "of_y_offset")

        # 将 x_var 与 x_vars 关联：x_var == j 当且仅当 x_vars[j] == 1
        for j in range(size):
            eq = model.NewBoolVar(f"of_x_eq_{j}")
            model.Add(x_var == j).OnlyEnforceIf(eq)
            model.Add(x_var != j).OnlyEnforceIf(eq.Not())
            model.Add(x_vars[j] == 1).OnlyEnforceIf(eq)
            model.Add(x_vars[j] == 0).OnlyEnforceIf(eq.Not())

        # 将 y_var 与 y_vars 关联
        for j in range(size):
            eq = model.NewBoolVar(f"of_y_eq_{j}")
            model.Add(y_var == j).OnlyEnforceIf(eq)
            model.Add(y_var != j).OnlyEnforceIf(eq.Not())
            model.Add(y_vars[j] == 1).OnlyEnforceIf(eq)
            model.Add(y_vars[j] == 0).OnlyEnforceIf(eq.Not())

        # ---------- 4. 为每个 (x, y) 组合创建全局选择变量 ----------
        # 每个组合对应一个布尔变量，表示该组合被选中
        combo_vars = []
        for x in range(size):
            for y in range(size):
                combo = model.NewBoolVar(f"of_combo_{x}_{y}")
                combo_vars.append(combo)
                # 当 combo 为真时，强制 x_var == x 且 y_var == y
                model.Add(x_var == x).OnlyEnforceIf(combo)
                model.Add(y_var == y).OnlyEnforceIf(combo)
                # 当 combo 为假时，不强制（但不能同时有两个 combo 为真，下面会约束）

        # 恰好一个组合被选中
        model.Add(sum(combo_vars) == 1).OnlyEnforceIf(s)

        # ---------- 5. 为每个线索格创建约束 ----------
        for pos, obj in board("C", mode="obj", key=MASTER_BOARD_KEY):
            if not isinstance(obj, ValueOF):
                continue

            val_var = board.get_variable(pos, special="raw")
            if val_var is None:
                continue

            # 该线索格必须是非雷
            model.Add(val_var == 0).OnlyEnforceIf(s)

            # 对于每个可能的 (x, y) 组合，当该组合被选中时，约束邻居雷数 == obj.count
            idx = 0
            for x in range(size):
                for y in range(size):
                    combo = combo_vars[idx]
                    idx += 1

                    new_row = (pos.row + x) % size
                    new_col = (pos.col + y) % size
                    new_pos = board.get_pos(new_row, new_col, MASTER_BOARD_KEY)

                    # 计算周围八格的雷数（使用变量）
                    neighbor_vars = []
                    for n in new_pos.neighbors(2):
                        if board.in_bounds(n):
                            n_var = board.get_variable(n)
                            if n_var is not None:
                                neighbor_vars.append(n_var)

                    neighbor_sum = sum(neighbor_vars) if neighbor_vars else 0

                    # 约束：当 combo 为真时，邻居雷数 == obj.count
                    model.Add(neighbor_sum == obj.count).OnlyEnforceIf([combo, s])


class ValueOF(AbstractClueValue):
    """[OF] 偏移规则线索值类"""

    id = RuleOF.id

    def __init__(
        self,
        pos: "Position",
        count: int = 0,
        x_val: int = 0,
        y_val: int = 0,
        code: Optional[bytes] = None,
    ) -> None:
        super().__init__(pos, code or b"")
        if code is not None and len(code) >= 3:
            # 从字节码解码
            self.count = code[0]
            self.x_val = code[1]
            self.y_val = code[2]
        else:
            self.count = count
            self.x_val = x_val
            self.y_val = y_val
        self.value = SingleIntValue(self.count)

    @classmethod
    def from_json(cls, pos: "Position", data: "JSONObject") -> Self:
        """从 JSON 恢复线索值对象"""
        from minesweepervariants.json_object import deep_unwrap
        from minesweepervariants.utils.value_template import SingleIntValue, is_value_template

        _data = deep_unwrap(data)
        # 优先处理自定义字典格式
        if isinstance(_data, dict):
            count = _data.get("count", 0)
            x_val = _data.get("x_val", 0)
            y_val = _data.get("y_val", 0)
            return cls(pos, count=count, x_val=x_val, y_val=y_val)
        # 兼容 SingleIntValue 模板格式
        if is_value_template(_data):
            val = SingleIntValue.try_from(_data)
            if val is not None:
                return cls(pos, count=val.value)
        raise TypeError(f"Invalid data for ValueOF: {data}")

    def json(self) -> "JSONObject":
        """导出为 JSON"""
        from minesweepervariants.immutable_dict import ImmutableDict
        return ImmutableDict({
            "count": self.count,
            "x_val": self.x_val,
            "y_val": self.y_val,
        })

    def __repr__(self) -> str:
        return str(self.count)

    def compose(self, board: "Board") -> Element:
        """渲染为图像元素"""
        from minesweepervariants.utils.image_template import get_col, get_text, get_dummy
        return get_col(
            get_dummy(height=0.3),
            get_text(str(self.count), color=("#FFFFFF", "#000000")),
            get_dummy(height=0.3),
        )

    def web_component(self, board: "Board") -> Element:
        """渲染为网页组件"""
        from minesweepervariants.utils.web_template import Number
        return Number(str(self.count))

    def tag(self, board: "Board") -> bytes:
        """角标显示偏移量信息"""
        return f"({self.x_val},{self.y_val})".encode("ascii")

    def high_light(self, board: "Board") -> List["Position"]:
        """高亮显示偏移后位置及其周围八格"""
        if board is None:
            return []
        size = board.boundary(MASTER_BOARD_KEY).row + 1
        if size <= 0:
            return []
        # 计算偏移后位置
        new_row = (self.pos.row + self.x_val) % size
        new_col = (self.pos.col + self.y_val) % size
        new_pos = board.get_pos(new_row, new_col, MASTER_BOARD_KEY)
        if not board.in_bounds(new_pos):
            return []
        # 返回偏移后位置周围八格
        return [n for n in new_pos.neighbors(2) if board.in_bounds(n)]

    def create_constraints(self, board: "Board", switch: "Switch") -> None:
        """线索值约束（已在规则类中统一处理，此处留空）"""
        # 约束已在 RuleOF.create_constraints 中统一构建
        pass
