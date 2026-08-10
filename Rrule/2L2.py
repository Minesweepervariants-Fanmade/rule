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
  4. 误差标记位置的主格必须为非雷
"""

from typing import Self

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position, Size
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import JSONObject, deep_unwrap
from minesweepervariants.utils.impl_obj import VALUE_CIRCLE, VALUE_CROSS
from minesweepervariants.utils.tool import get_logger, get_random
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template

NAME_2L2 = "2L2"


def generate_error_positions(n: int, valid_positions: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """
    从有效位置中生成每行每列恰好两个误差标记的位置。
    使用二分图匹配算法（Hopcroft-Karp）或简单的随机采样+验证。
    """
    random = get_random()
    max_attempts = 20000
    
    # 构建每行的候选列
    row_candidates = [[] for _ in range(n)]
    for r, c in valid_positions:
        row_candidates[r].append(c)
    
    # 如果某行候选少于2个，无法满足要求
    for r in range(n):
        if len(row_candidates[r]) < 2:
            return []
    
    for _ in range(max_attempts):
        # 为每行选择两个不同的列
        row_cols = []
        valid = True
        for r in range(n):
            candidates = row_candidates[r]
            if len(candidates) < 2:
                valid = False
                break
            selected = random.sample(candidates, 2)
            row_cols.append(selected)
        if not valid:
            continue
        
        # 统计每列被选中的次数
        col_counts = [0] * n
        for cols in row_cols:
            for c in cols:
                col_counts[c] += 1
        
        if all(count == 2 for count in col_counts):
            result = []
            for r, cols in enumerate(row_cols):
                for c in cols:
                    result.append((r, c))
            return result
    
    # 确定性方法：逐行选择，尽量平衡列
    result = []
    col_counts = [0] * n
    for r in range(n):
        candidates = sorted(row_candidates[r], key=lambda c: col_counts[c])
        # 选择两个计数最小的列
        selected = candidates[:2]
        result.append((r, selected[0]))
        result.append((r, selected[1]))
        col_counts[selected[0]] += 1
        col_counts[selected[1]] += 1
    
    # 检查是否每列恰好被选中两次
    if all(count == 2 for count in col_counts):
        return result
    
    return []


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
        bound = board.boundary()
        if bound.row != bound.col:
            raise ValueError("2L2 要求正方形题板")
        for key in board.get_interactive_keys():
            _bound = board.boundary(key)
            if _bound.row != bound.row or _bound.col != bound.col:
                raise ValueError("所有交互题板尺寸必须一致")

        size = Size(bound.row + 1, bound.col + 1)
        board.generate_board(NAME_2L2, size)
        board.set_config(NAME_2L2, "pos_label", False)

    def fill(self, board: 'Board') -> 'Board':
        """填充所有线索格，并为副板设置误差标记"""
        self.init_clear(board)
        random = get_random()
        bound = board.boundary()
        n = bound.row + 1
        logger = get_logger()

        # 1. 收集所有非雷格（类型不为 'F'）及其真实值
        true_values = {}
        non_mine_positions = []
        for key in board.get_interactive_keys():
            for row in range(n):
                for col in range(n):
                    pos = board.get_pos(row, col, key)
                    if pos is None:
                        continue
                    if board.get_type(pos) != "F":
                        true_value = board.batch(pos.neighbors(2), mode="type").count("F")
                        true_values[(row, col)] = true_value
                        non_mine_positions.append((row, col))

        logger.debug(f"[2L2] 非雷格数量: {len(non_mine_positions)}")

        if len(non_mine_positions) < 2 * n:
            logger.warning("[2L2] 非雷格数量不足，跳过本次填充")
            return board

        # 2. 使用 generate_error_positions 生成每行每列恰好两个误差标记
        # 传入非雷格位置作为有效候选
        pos_list = generate_error_positions(n, non_mine_positions)
        if not pos_list:
            logger.warning("[2L2] 无法生成满足条件的误差标记位置，跳过本次填充")
            return board
        pos_set = set(pos_list)

        # 3. 标记副板
        for pos, _ in board(key=NAME_2L2):
            if (pos.row, pos.col) in pos_set:
                board.set_value(pos, VALUE_CIRCLE)
                logger.debug(f"[2L2] put O at {pos}")
            else:
                board.set_value(pos, VALUE_CROSS)
                logger.debug(f"[2L2] put X at {pos}")

        # 4. 为每个非雷格生成线索值
        for pos, _ in board("N", special='raw'):
            true_value = true_values.get((pos.row, pos.col), 0)
            is_error = (pos.row, pos.col) in pos_set

            if is_error:
                candidates = [true_value - 1, true_value + 1]
                candidates = [v for v in candidates if 0 <= v <= 8]
                if not candidates:
                    if true_value == 0:
                        display_value = 1
                    elif true_value == 8:
                        display_value = 7
                    else:
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

        # 行约束：每行恰好两个 CIRCLE
        for pos in board.get_row_pos(bound):
            line = board.get_col_pos(pos)
            line_vars = board.batch(line, mode="variable", drop_none=True)
            model.Add(sum(line_vars) == 2).OnlyEnforceIf(s)

        # 列约束：每列恰好两个 CIRCLE
        for pos in board.get_col_pos(bound):
            line = board.get_row_pos(pos)
            line_vars = board.batch(line, mode="variable", drop_none=True)
            model.Add(sum(line_vars) == 2).OnlyEnforceIf(s)

        # 强制所有副板位置的主格为非雷（因为副板标记位置都对应主板的线索格）
        for pos, _ in board(key=NAME_2L2):
            main_pos = board.get_pos(pos.row, pos.col)
            main_var = board.get_variable(main_pos)
            if main_var is not None:
                model.Add(main_var == 0).OnlyEnforceIf(s)


class Value2L2(AbstractClueValue):
    """2L2 线索值类"""

    id = Rule2L2.id

    def __init__(self, pos: Position, code: bytes | None = None):
        super().__init__(pos, code or b'')
        self.pos = pos
        self.display_value = code[0] if code else 0
        self.value = SingleIntValue(self.display_value)
        self.neighbor = pos.neighbors(2)

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
        return self.neighbor

    def create_constraints(self, board: 'Board', switch: Switch) -> None:
        """约束：真实雷数 = 显示值（非误差） 或 显示值 ± 1（误差）"""
        model = board.get_model()
        s = switch.get(model, self)

        marker_pos = board.get_pos(self.pos.row, self.pos.col, NAME_2L2)
        marker_var = board.get_variable(marker_pos)
        if marker_var is None:
            return

        neighbor_vars = board.batch(self.neighbor, mode="variable", drop_none=True)
        true_sum = sum(neighbor_vars) if neighbor_vars else 0

        # 非误差：真实值 == 显示值
        model.Add(true_sum == self.display_value).OnlyEnforceIf([marker_var.Not(), s])

        # 误差：真实值 == 显示值 + 1 或 显示值 - 1
        tmp_plus = model.NewBoolVar("tmp_plus")
        tmp_minus = model.NewBoolVar("tmp_minus")
        model.Add(true_sum == self.display_value + 1).OnlyEnforceIf([tmp_plus, s])
        model.Add(true_sum == self.display_value - 1).OnlyEnforceIf([tmp_minus, s])
        model.AddBoolOr([tmp_plus, tmp_minus]).OnlyEnforceIf([marker_var, s])
