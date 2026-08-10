#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026-08-10
# @Author  : Gat (992600401)
# @FileName: 2L2.py
"""
[2L2] 每行每列恰有两个误差线索，误差线索比实际值大1或小1

实现说明：
- 使用副板标记误差位置（VALUE_CIRCLE 表示误差，VALUE_CROSS 表示非误差）
- fill 阶段：随机选择每行每列各两个位置作为误差标记，并生成对应的显示值
- create_constraints 阶段：
  1. 副板每行每列恰好两个 CIRCLE
  2. 线索格若为误差（对应副板为 CIRCLE），则真实值 = 显示值 ± 1
  3. 线索格若非误差（对应副板为 CROSS），则真实值 = 显示值
  4. 误差标记位置的主格必须为非雷
"""

import random
from typing import Self

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import JSONObject, deep_unwrap
from minesweepervariants.size import Size
from minesweepervariants.utils.impl_obj import VALUE_CIRCLE, VALUE_CROSS
from minesweepervariants.utils.tool import get_logger, get_random
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template

NAME_2L2 = "2L2"


def generate_error_positions(n: int, valid_positions: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """
    从有效位置中生成每行每列恰好两个误差标记的位置。
    使用递归回溯算法，如果失败则使用随机采样作为后备。

    参数:
        n: 棋盘大小 (n x n)
        valid_positions: 所有非雷格的位置列表，每个元素为 (row, col)

    返回:
        选中的位置列表，每个元素为 (row, col)，长度为 2*n
        如果无法找到，返回空列表
    """
    rng = get_random()

    # 构建每行的候选列列表（去重，且为有效非雷格）
    row_candidates = [[] for _ in range(n)]
    col_candidates = [[] for _ in range(n)]
    for r, c in valid_positions:
        if r < n and c < n:
            if c not in row_candidates[r]:
                row_candidates[r].append(c)
            if r not in col_candidates[c]:
                col_candidates[c].append(r)

    # 如果某行或某列候选少于2个，无法满足要求
    for r in range(n):
        if len(row_candidates[r]) < 2:
            return []
    for c in range(n):
        if len(col_candidates[c]) < 2:
            return []

    # 随机打乱每行的候选列，增加随机性
    for r in range(n):
        rng.shuffle(row_candidates[r])

    # 递归回溯：尝试为每行选择两个列
    selected = []  # 最终选中的 (row, col) 列表
    col_count = [0] * n  # 每列当前被选中的次数

    # 按行候选数量升序排序，优先处理选择最少的行
    row_order = list(range(n))
    row_order.sort(key=lambda r: len(row_candidates[r]))

    def dfs(idx: int) -> bool:
        """尝试为第 row_order[idx] 行选择两个列"""
        if idx == n:
            # 所有行都已选择，检查每列是否恰好被选中2次
            return all(c == 2 for c in col_count)

        row = row_order[idx]
        candidates = row_candidates[row]
        # 按列当前使用次数升序排序（优先使用剩余容量多的列）
        candidates = sorted(candidates, key=lambda c: col_count[c])

        for i in range(len(candidates)):
            c1 = candidates[i]
            if col_count[c1] >= 2:
                continue
            for j in range(i + 1, len(candidates)):
                c2 = candidates[j]
                if c2 == c1 or col_count[c2] >= 2:
                    continue
                # 尝试选择 (c1, c2)
                col_count[c1] += 1
                col_count[c2] += 1
                selected.append((row, c1))
                selected.append((row, c2))

                if dfs(idx + 1):
                    return True

                # 回溯
                selected.pop()
                selected.pop()
                col_count[c1] -= 1
                col_count[c2] -= 1
        return False

    # 从第0行开始搜索
    if dfs(0):
        return selected

    # ----- 后备方案：随机采样 -----
    # 如果回溯失败，尝试随机采样
    max_attempts = 5000
    for _ in range(max_attempts):
        # 为每行选择两个列
        temp_selected = []
        temp_col_count = [0] * n
        possible = True

        # 按行顺序选择，但每次从候选列中随机选两个
        for r in range(n):
            candidates = row_candidates[r][:]
            rng.shuffle(candidates)
            # 找两个可用列
            chosen = []
            for c in candidates:
                if temp_col_count[c] < 2:
                    chosen.append(c)
                    if len(chosen) == 2:
                        break
            if len(chosen) < 2:
                possible = False
                break
            temp_selected.append((r, chosen[0]))
            temp_selected.append((r, chosen[1]))
            temp_col_count[chosen[0]] += 1
            temp_col_count[chosen[1]] += 1

        if possible and all(c == 2 for c in temp_col_count):
            return temp_selected

    return []


class Rule2L2(AbstractClueRule):
    """[2L2] 每行每列恰有两个误差线索"""

    id = "2L2"
    name = "2L2"
    name.zh_CN = "每行每列恰有两个误差线索"
    doc = "Each row and column has exactly two error clues, where error clues are off by ±1 from the true value."
    doc.zh_CN = "每行每列恰有两个误差线索，误差线索比实际值大1或小1。"
    tags = ["Creative", "Local", "Construction"]
    creation_time = "2026-08-10"
    author = ("Gat", 992600401)

    def __init__(self):
        super().__init__()

    def fill(self, board: 'Board') -> 'Board':
        """填充题板：随机选择每行每列各两个非雷格作为误差标记，并设置线索值"""
        logger = get_logger()
        size = board.size
        if size.row != size.col:
            raise ValueError("2L2 要求正方形题板")
        n = size.row

        # 获取主板 key
        key = board.get_interactive_keys()[0]
        board.generate_board(NAME_2L2, size=size)
        board.set_config(NAME_2L2, "pos_label", False)

        # 获取所有非雷格的位置
        non_mine_positions = []
        for pos, typ in board("N", special='raw'):
            non_mine_positions.append((pos.row, pos.col))

        # 随机打乱
        rng = get_random()
        rng.shuffle(non_mine_positions)

        # 生成误差标记位置
        selected = generate_error_positions(n, non_mine_positions)
        if not selected:
            logger.warning("[2L2] 无法生成满足条件的误差标记位置，跳过本次填充")
            return board

        # 在副板上标记 CIRCLE 和 CROSS
        for r in range(n):
            for c in range(n):
                pos = board.get_pos(r, c, NAME_2L2)
                if (r, c) in selected:
                    board.set_value(pos, VALUE_CIRCLE)
                    logger.debug(f"[2L2] put O at {pos}")
                else:
                    board.set_value(pos, VALUE_CROSS)
                    logger.debug(f"[2L2] put X at {pos}")

        # 设置线索值：对于非雷格，根据是否为误差标记生成显示值
        for pos, _ in board("N", special='raw'):
            marker_pos = board.get_pos(pos.row, pos.col, NAME_2L2)
            marker_obj = board.get_value(marker_pos)
            is_error = (marker_obj == VALUE_CIRCLE)

            # 计算真实雷数
            neighbor = pos.neighbors(2)
            neighbor_vars = board.batch(neighbor, mode="variable", drop_none=True)
            true_count = sum(neighbor_vars) if neighbor_vars else 0

            if is_error:
                # 误差：显示值 = 真实值 ± 1，随机选择加或减，但保证显示值 >= 0
                if true_count > 0 and rng.random() < 0.5:
                    display_value = true_count - 1
                else:
                    display_value = true_count + 1
                # 确保显示值非负
                if display_value < 0:
                    display_value = true_count + 1
            else:
                display_value = true_count

            # 限制显示值范围 0-8
            display_value = max(0, min(8, display_value))
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

        # 强制副板标记为 CIRCLE 的位置对应的主格为非雷
        for pos, obj in board(key=NAME_2L2, mode="obj"):
            if obj != VALUE_CIRCLE:
                continue
            main_pos = board.get_pos(pos.row, pos.col)
            main_var = board.get_variable(main_pos)
            if main_var is not None:
                model.Add(main_var == 0).OnlyEnforceIf(s)

    def suggest_total(self, info: dict) -> None:
        """
        建议总雷数范围。
        每行每列需要 2 个非雷格作为误差标记，所以总雷数最多为总格子数 - 2*n。
        """
        ub = 0
        for key in info["interactive"]:
            total_cells = info["total"][key]
            ub += total_cells

        # 获取棋盘大小 n
        n = 0
        for key in info["interactive"]:
            size = info["size"][key]
            n = min(size[0], size[1])
            break
        if n == 0:
            return

        # 最大雷数 = 总格子数 - 2*n（每行每列需要 2 个非雷格）
        max_mines = ub - 2 * n
        if max_mines < 0:
            max_mines = 0

        # 建议雷数在 0 到 max_mines 之间，偏向中间值
        target = max_mines // 2
        info["soft_fn"](target, 0)


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
