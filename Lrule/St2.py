#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/18
# @Author  : DeepSeek Agent
# @FileName: St2.py

"""
[St2] 状态2：一个雷的左右和上下的状态相同与否的状态相同。（前加~改成非雷，后加~改成不同，可以都加）（第A列，最后一列，第1行，最后一行的雷/非雷无约束）
"""

from typing import Optional
from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.position import Position


class _St2Base(AbstractMinesRule):
    """
    St2 规则基类，包含核心逻辑。
    子类通过设置 target_is_mine 和 require_same 来控制行为。
    """
    # 基类不设置 id，由子类设置
    name = "状态2"
    name.zh_CN = "状态2"
    doc = "For a mine, whether its left/right states are the same matches whether its up/down states are the same. (~ prefix: non-mine, ~ suffix: different)"
    doc.zh_CN = "一个雷的左右和上下的状态相同与否的状态相同。（前加~改成非雷，后加~改成不同，可以都加）"
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
        添加约束：对于每个满足条件的位置，其左右状态相同与否与其上下状态相同与否满足指定关系。
        """
        model = board.get_model()
        if model is None:
            return

        # 获取该规则对应的开关变量
        rule_switch = switch.get(model, self)
        # 强制规则开关为真，确保规则始终生效
        model.Add(rule_switch == 1)

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
                    pos = Position(col, row, board_key=key)

                    if not board.is_valid(pos):
                        continue

                    # 第A列（col=0）、最后一列（col=cols-1）、
                    # 第1行（row=0）、最后一行（row=rows-1）无约束
                    if col == 0 or col == cols - 1 or row == 0 or row == rows - 1:
                        continue

                    # 获取当前格的变量
                    var = board.get_variable(pos)
                    if var is None:
                        continue

                    # 获取左、右、上、下四个邻居的位置
                    left_pos = Position(col - 1, row, board_key=key)
                    right_pos = Position(col + 1, row, board_key=key)
                    up_pos = Position(col, row - 1, board_key=key)
                    down_pos = Position(col, row + 1, board_key=key)

                    # 检查四个邻居是否都有效
                    if not (board.is_valid(left_pos) and board.is_valid(right_pos) and
                            board.is_valid(up_pos) and board.is_valid(down_pos)):
                        continue

                    left_var = board.get_variable(left_pos)
                    right_var = board.get_variable(right_pos)
                    up_var = board.get_variable(up_pos)
                    down_var = board.get_variable(down_pos)

                    if left_var is None or right_var is None or up_var is None or down_var is None:
                        continue

                    # 构建条件：根据 target_is_mine 决定条件变量
                    if self.target_is_mine:
                        condition = var
                    else:
                        condition = var.Not()

                    # 使用布尔变量表示左右相等和上下相等
                    h_same = model.NewBoolVar(f"h_same_{pos}")
                    v_same = model.NewBoolVar(f"v_same_{pos}")

                    # h_same == 1 当且仅当 left_var == right_var
                    model.Add(h_same == 1).OnlyEnforceIf([left_var, right_var])
                    model.Add(h_same == 1).OnlyEnforceIf([left_var.Not(), right_var.Not()])
                    model.Add(h_same == 0).OnlyEnforceIf([left_var, right_var.Not()])
                    model.Add(h_same == 0).OnlyEnforceIf([left_var.Not(), right_var])

                    # v_same == 1 当且仅当 up_var == down_var
                    model.Add(v_same == 1).OnlyEnforceIf([up_var, down_var])
                    model.Add(v_same == 1).OnlyEnforceIf([up_var.Not(), down_var.Not()])
                    model.Add(v_same == 0).OnlyEnforceIf([up_var, down_var.Not()])
                    model.Add(v_same == 0).OnlyEnforceIf([up_var.Not(), down_var])

                    # 根据 require_same 决定关系
                    if self.require_same:
                        # condition 为真且规则开关打开时，h_same 必须等于 v_same
                        model.Add(h_same == v_same).OnlyEnforceIf([condition, rule_switch])
                    else:
                        # condition 为真且规则开关打开时，h_same 必须不等于 v_same（异或）
                        model.Add(h_same + v_same == 1).OnlyEnforceIf([condition, rule_switch])

    def suggest_total(self, info: dict):
        """此规则不强制雷总数，留空即可。"""
        pass

    def init_board(self, board: Board) -> bool:
        """初始化题板时无需特殊操作。"""
        return True

    def init_clear(self, board: Board) -> None:
        """清除阶段无需特殊操作。"""
        pass

    def combine(self, other) -> Optional['_St2Base']:
        """规则合并优化：不支持合并。"""
        return None

    def get_deps(self) -> list[str]:
        """无依赖。"""
        return []


class St2(_St2Base):
    """
    [St2] 原版：对于每个雷，其左右状态相同当且仅当其上下状态相同。
    使用: -c St2
    """
    id = "St2"
    doc = "For a mine, left/right same iff up/down same. (No constraint for column A, last column, row 1, last row)"
    doc.zh_CN = "一个雷的左右和上下的状态相同与否的状态相同。（前加~改成非雷，后加~改成不同，可以都加）（第A列，最后一列，第1行，最后一行的雷/非雷无约束）"

    def __init__(self, board: "Board" = None, data: str = None) -> None:
        super().__init__(board, data)
        self.target_is_mine = True
        self.require_same = True


class PrefixSt2(_St2Base):
    """
    [~St2] 前加~变体：对于每个非雷，其左右状态相同当且仅当其上下状态相同。
    使用: -c ~St2
    """
    id = "~St2"
    name = "~状态2"
    name.zh_CN = "~状态2"
    doc = "For a non-mine, left/right same iff up/down same."
    doc.zh_CN = "一个非雷的左右和上下的状态相同与否的状态相同。（前加~）"

    def __init__(self, board: "Board" = None, data: str = None) -> None:
        super().__init__(board, data)
        self.target_is_mine = False
        self.require_same = True


class SuffixSt2(_St2Base):
    """
    [St2~] 后加~变体：对于每个雷，其左右状态相同当且仅当其上下状态不同。
    使用: -c St2~
    """
    id = "St2~"
    name = "状态2~"
    name.zh_CN = "状态2~"
    doc = "For a mine, left/right same iff up/down different."
    doc.zh_CN = "一个雷的左右和上下的状态相同与否的状态不同。（后加~）"

    def __init__(self, board: "Board" = None, data: str = None) -> None:
        super().__init__(board, data)
        self.target_is_mine = True
        self.require_same = False


class BothSt2(_St2Base):
    """
    [~St2~] 前后都加变体：对于每个非雷，其左右状态相同当且仅当其上下状态不同。
    使用: -c ~St2~
    """
    id = "~St2~"
    name = "~状态2~"
    name.zh_CN = "~状态2~"
    doc = "For a non-mine, left/right same iff up/down different."
    doc.zh_CN = "一个非雷的左右和上下的状态相同与否的状态不同。（前后都加~）"

    def __init__(self, board: "Board" = None, data: str = None) -> None:
        super().__init__(board, data)
        self.target_is_mine = False
        self.require_same = False
