#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/12
# @Author  : Assistant
# @FileName: St1.py

"""
[St1] 状态1：一个雷的左边一格和下边一格状态相同。
（前加~改成非雷，后加~改成不同，可以都加）
（第A列和最后一行的雷/非雷无约束）
"""

from typing import Optional
from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board


class _St1Base(AbstractMinesRule):
    """
    St1 规则基类，包含核心逻辑。
    子类通过设置 target_is_mine 和 require_same 来控制行为。
    """
    # 基类不设置 id，由子类设置
    name = "状态1"
    name.zh_CN = "状态1"
    doc = "A mine's left and down neighbors have the same state. (~ prefix: non-mine, ~ suffix: different)"
    doc.zh_CN = "一个雷的左边一格和下边一格状态相同。（前加~改成非雷，后加~改成不同，可以都加）"
    author = ("小中医 (3086842243)", 3086842243)
    tags = ["Local", "Mine-Position"]
    creation_time = "2026-07-11"

    def __init__(self, board: "Board" = None, data: str = None) -> None:
        super().__init__(board, data)
        # 默认值：约束对象是雷，要求状态相同
        # 子类在 __init__ 中覆盖这些值
        self.target_is_mine = True
        self.require_same = True

    def create_constraints(self, board: 'Board', switch):
        """
        添加约束：对于每个满足条件的位置，其左边一格和下边一格状态满足指定关系。
        """
        model = board.get_model()
        if model is None:
            return

        rule_switch = switch.get(model, self)

        # 遍历所有交互式键（题板）
        for key in board.get_interactive_keys():
            # 获取该键的边界（右下角位置）
            boundary = board.boundary(key=key)
            if boundary is None:
                continue
            rows = boundary.row + 1
            cols = boundary.col + 1

            # 遍历所有位置
            for row in range(rows):
                for col in range(cols):
                    from minesweepervariants.position import Position
                    pos = Position(col, row, board_key=key)

                    if not board.is_valid(pos):
                        continue

                    # 第A列（col=0）或最后一行（row=rows-1）无约束
                    if col == 0 or row == rows - 1:
                        continue

                    # 获取当前格的变量
                    var = board.get_variable(pos)
                    if var is None:
                        continue

                    # 获取左边一格和下边一格的位置
                    left_pos = Position(col - 1, row, board_key=key)
                    down_pos = Position(col, row + 1, board_key=key)

                    # 检查这两个位置是否有效（理论上一定有效，因为 col>0 且 row<rows-1）
                    if not board.is_valid(left_pos) or not board.is_valid(down_pos):
                        continue

                    left_var = board.get_variable(left_pos)
                    down_var = board.get_variable(down_pos)

                    if left_var is None or down_var is None:
                        continue

                    # 构建条件：根据 target_is_mine 决定条件变量
                    if self.target_is_mine:
                        condition = var
                    else:
                        condition = var.Not()

                    # 根据 require_same 决定是相等还是不等
                    if self.require_same:
                        model.Add(left_var == down_var).OnlyEnforceIf([condition, rule_switch])
                    else:
                        model.Add(left_var != down_var).OnlyEnforceIf([condition, rule_switch])

    def suggest_total(self, info: dict):
        """此规则不强制雷总数，留空即可。"""
        pass

    def init_board(self, board: Board) -> bool:
        """初始化题板时无需特殊操作。"""
        return True

    def init_clear(self, board: Board) -> None:
        """清除阶段无需特殊操作。"""
        pass

    def combine(self, other) -> Optional['_St1Base']:
        """规则合并优化：不支持合并。"""
        return None

    def get_deps(self) -> list[str]:
        """无依赖。"""
        return []


class St1(_St1Base):
    """
    [St1] 原版：对于每个雷，左边一格和下边一格状态相同。
    使用: -c St1
    """
    id = "St1"

    def __init__(self, board: "Board" = None, data: str = None) -> None:
        super().__init__(board, data)
        self.target_is_mine = True
        self.require_same = True


class PrefixSt1(_St1Base):
    """
    [~St1] 前加~变体：对于每个非雷，左边一格和下边一格状态相同。
    使用: -c ~St1
    """
    id = "~St1"
    name = "~状态1"
    name.zh_CN = "~状态1"
    doc = "A non-mine's left and down neighbors have the same state."
    doc.zh_CN = "一个非雷的左边一格和下边一格状态相同。（前加~）"

    def __init__(self, board: "Board" = None, data: str = None) -> None:
        super().__init__(board, data)
        self.target_is_mine = False
        self.require_same = True


class SuffixSt1(_St1Base):
    """
    [St1~] 后加~变体：对于每个雷，左边一格和下边一格状态不同。
    使用: -c St1~
    """
    id = "St1~"
    name = "状态1~"
    name.zh_CN = "状态1~"
    doc = "A mine's left and down neighbors have different states."
    doc.zh_CN = "一个雷的左边一格和下边一格状态不同。（后加~）"

    def __init__(self, board: "Board" = None, data: str = None) -> None:
        super().__init__(board, data)
        self.target_is_mine = True
        self.require_same = False


class BothSt1(_St1Base):
    """
    [~St1~] 前后都加变体：对于每个非雷，左边一格和下边一格状态不同。
    使用: -c ~St1~
    """
    id = "~St1~"
    name = "~状态1~"
    name.zh_CN = "~状态1~"
    doc = "A non-mine's left and down neighbors have different states."
    doc.zh_CN = "一个非雷的左边一格和下边一格状态不同。（前后都加~）"

    def __init__(self, board: "Board" = None, data: str = None) -> None:
        super().__init__(board, data)
        self.target_is_mine = False
        self.require_same = False
