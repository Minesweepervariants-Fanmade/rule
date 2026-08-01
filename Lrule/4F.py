#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/08/01 15:44
# @Author  : NT (2201963934)
# @FileName: 4F.py
"""
[4F]费曼图 (Feynman Diagram)：从题版左侧发出桥，向右侧运动，桥的延伸方向不能改变，
当两座反向斜桥在同一格相遇，后续会变成一座直桥，直桥随时可以分裂成两座方向相反的斜桥。
所有桥只能在遇到题版边缘（包括上下）时停止。

实现思路：
- 每个雷格子具有方向状态：水平(1)、右上(2)、右下(3)，无雷为0
- 方向在传播过程中保持不变（除非在合并/分裂点）
- 合并：两个斜向路径（一个右上、一个右下）汇合为水平路径
- 分裂：水平路径分裂为两个斜向路径（一个右上、一个右下）
- 路径从左边界开始，遇到边界（包括上下）时停止

参考实现：2B.py 的 create_constraints_real 方法
"""

from typing import Dict, List, Optional, Tuple
from ortools.sat.python import cp_model

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.position import Position


class Rule4F(AbstractMinesRule):
    id = "4F"
    aliases = ("Feynman", "费曼")
    name = "Feynman Diagram"
    name.zh_CN = "费曼图"
    doc = "Bridges emit from the left side of the board and move to the right. The direction of a bridge cannot change. When two opposite diagonal bridges meet at the same cell, they become a straight bridge. A straight bridge can split into two opposite diagonal bridges at any time. All bridges stop only when they encounter the board edge (including top and bottom)."
    doc.zh_CN = "从题版左侧发出桥，向右侧运动，桥的延伸方向不能改变，当两座反向斜桥在同一格相遇，后续会变成一座直桥，直桥随时可以分裂成两座方向相反的斜桥。所有桥只能在遇到题版边缘（包括上下）时停止。"
    author = ("NT", 2201963934)
    tags = ["Original", "Global", "Construction", "Connectivity"]
    creation_time = "2026-08-01"

    def __init__(self, board: Optional['Board'] = None, data: Optional[str] = None) -> None:
        super().__init__(board, data)
        # 允许多种实现风格，默认为标准费曼图
        if data:
            data = data.lower()
        match data:
            case None:
                self._impl_style = "standard"
            case "nt" | "standard":
                self._impl_style = "standard"
            case _:
                raise ValueError(f"未知的实现风格: {data}")

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        """
        创建费曼图规则的核心约束。
        使用状态变量表示每个格子的方向，并约束路径的传播、合并与分裂。
        """
        match self._impl_style:
            case "standard":
                return self._create_constraints_standard(board, switch)
            case _:
                raise ValueError(f"未知的实现风格: {self._impl_style}")

    def _create_constraints_standard(self, board: 'Board', switch: 'Switch') -> None:
        """
        标准实现：使用三状态方向变量，约束路径传播、合并与分裂。
        """
        model = board.get_model()
        s = switch.get(model, self)

        # 为每个位置创建方向状态变量
        # 0: 无雷  1: 水平（直桥）  2: 右上斜桥  3: 右下斜桥
        state: Dict[Position, cp_model.IntVar] = {}
        for pos, _ in board():
            state[pos] = model.NewIntVar(0, 3, f"state_{pos}")

        # 约束：如果位置有雷（变量为1），则状态必须非0；否则状态必须为0
        for pos, _ in board():
            var = board.get_variable(pos)
            if var is None:
                continue
            # var == 1  => state != 0
            model.Add(state[pos] != 0).OnlyEnforceIf([var, s])
            # var == 0  => state == 0
            model.Add(state[pos] == 0).OnlyEnforceIf([var.Not(), s])

        # 对每个交互式题板分别处理
        for key in board.get_interactive_keys():
            boundary = board.boundary(key)
            cols = boundary.col + 1
            rows = boundary.row + 1

            # ---------- 1. 每列雷数相同（桥的宽度一致） ----------
            col_sums = []
            for col_idx in range(cols):
                col_pos = boundary.left(col_idx)
                col_cells = board.get_col_pos(col_pos)
                col_vars = [board.get_variable(p) for p in col_cells if board.get_variable(p) is not None]
                col_sum = sum(col_vars)
                col_sums.append(col_sum)
            for i in range(1, len(col_sums)):
                model.Add(col_sums[i] == col_sums[0]).OnlyEnforceIf(s)

            # ---------- 2. 获取每列中雷的位置索引列表 ----------
            # 使用 _get_index 辅助函数将每列的雷位置转换为索引数组
            col_indices: List[List[cp_model.IntVar]] = []
            for col_idx in range(cols):
                col_pos = boundary.left(col_idx)
                col_cells = board.get_col_pos(col_pos)
                # 过滤出有效的雷变量
                col_vars = [
                    board.get_variable(p) for p in col_cells
                    if board.get_variable(p) is not None
                ]
                if col_vars:
                    idx_vars = _get_index(col_vars, model, f"{key}_{col_pos}")
                    col_indices.append(idx_vars)
                else:
                    # 空列：使用空列表
                    col_indices.append([])

            # ---------- 3. 约束相邻列中雷的索引差值（路径连续性） ----------
            # 每个雷在下一列中必须有一个雷与之相邻（水平、右上或右下）
            for c in range(cols - 1):
                if not col_indices[c] or not col_indices[c + 1]:
                    continue
                # 对于当前列中的每个雷，约束其在下一列中对应的雷索引
                for r in range(min(len(col_indices[c]), len(col_indices[c + 1]))):
                    this_idx = col_indices[c][r]
                    next_idx = col_indices[c + 1][r]
                    # 差值范围 [-1, 1]：水平(0)、右上(-1)、右下(1)
                    diff = model.NewIntVar(-1, 1, f"diff_{key}_{c}_{r}")
                    model.Add(diff == next_idx - this_idx).OnlyEnforceIf(s)

            # ---------- 4. 方向传播约束（方向不能改变） ----------
            # 使用状态变量 state[pos] 表示方向
            # 对于每个雷，其右侧三个方向（水平、右上、右下）中必须至少有一个雷
            # 且该雷的方向必须与当前雷的方向一致（除非是合并/分裂点）
            for pos, _ in board():
                var = board.get_variable(pos)
                if var is None:
                    continue

                # 右侧三个候选位置
                right_positions = [
                    pos.right(),      # 水平
                    pos.right().up(), # 右上
                    pos.right().down() # 右下
                ]
                # 过滤出有效位置
                valid_right = [p for p in right_positions if board.in_bounds(p)]
                if not valid_right:
                    continue

                # 获取这些位置的变量和状态
                right_vars = [board.get_variable(p) for p in valid_right if board.get_variable(p) is not None]
                right_states = [state[p] for p in valid_right if p in state]

                if not right_vars or not right_states:
                    continue

                # 至少有一个右侧雷
                model.Add(sum(right_vars) >= 1).OnlyEnforceIf([var, s])

                # 方向传播：如果当前雷是水平(1)，则右侧雷中至少有一个是水平(1)
                # 如果当前雷是右上(2)，则右侧雷中至少有一个是右上(2)
                # 如果当前雷是右下(3)，则右侧雷中至少有一个是右下(3)
                for dir_val in [1, 2, 3]:
                    # 当前雷方向为 dir_val
                    # 右侧雷中至少有一个方向为 dir_val
                    # 创建布尔变量表示当前状态等于 dir_val
                    state_eq_dir = model.NewBoolVar(f"state_eq_{pos}_{dir_val}")
                    model.Add(state[pos] == dir_val).OnlyEnforceIf([state_eq_dir, s])
                    model.Add(state[pos] != dir_val).OnlyEnforceIf([state_eq_dir.Not(), s])
                    
                    right_dir_match = [
                        model.NewBoolVar(f"right_dir_{pos}_{dir_val}_{i}")
                        for i in range(len(right_states))
                    ]
                    for i, rs in enumerate(right_states):
                        model.Add(rs == dir_val).OnlyEnforceIf([right_dir_match[i], s])
                        model.Add(rs != dir_val).OnlyEnforceIf([right_dir_match[i].Not(), s])
                    model.Add(sum(right_dir_match) >= 1).OnlyEnforceIf(
                        [var, state_eq_dir, s]
                    )

            # ---------- 5. 汇合约束：两个斜向路径汇合为水平路径 ----------
            # 如果某个位置是水平(1)，且其左上和左下的位置都是斜向（2和3）
            # 则该位置是汇合点
            for pos, _ in board():
                var = board.get_variable(pos)
                if var is None:
                    continue

                # 左上和左下位置
                up_left = pos.left().up()
                down_left = pos.left().down()

                if not board.in_bounds(up_left) or not board.in_bounds(down_left):
                    continue
                if up_left not in state or down_left not in state:
                    continue

                # 如果当前是水平，且左上和左下都有雷，则它们必须是斜向（2和3）
                # 即：state[pos] == 1  => (state[up_left] == 2 且 state[down_left] == 3)
                # 或者 (state[up_left] == 3 且 state[down_left] == 2)
                is_merge = model.NewBoolVar(f"merge_{pos}")
                merge_cond_1 = model.NewBoolVar(f"merge_cond1_{pos}")
                merge_cond_2 = model.NewBoolVar(f"merge_cond2_{pos}")

                model.Add(state[up_left] == 2).OnlyEnforceIf([merge_cond_1, s])
                model.Add(state[down_left] == 3).OnlyEnforceIf([merge_cond_1, s])

                model.Add(state[up_left] == 3).OnlyEnforceIf([merge_cond_2, s])
                model.Add(state[down_left] == 2).OnlyEnforceIf([merge_cond_2, s])

                model.AddBoolOr([merge_cond_1, merge_cond_2]).OnlyEnforceIf([is_merge, s])
                model.AddBoolAnd([merge_cond_1.Not(), merge_cond_2.Not()]).OnlyEnforceIf([is_merge.Not(), s])

                # 如果当前是水平，则必须是汇合点（即左上和左下都是斜向）
                state_is_1_merge = model.NewBoolVar(f"state_is_1_merge_{pos}")
                model.Add(state[pos] == 1).OnlyEnforceIf([state_is_1_merge, s])
                model.Add(state[pos] != 1).OnlyEnforceIf([state_is_1_merge.Not(), s])
                model.Add(is_merge == 1).OnlyEnforceIf([var, state_is_1_merge, s])

            # ---------- 6. 分裂约束：水平路径分裂为两个斜向路径 ----------
            # 如果某个位置是水平(1)，且其右上的位置是右上(2)，右下的位置是右下(3)
            # 则该位置是分裂点
            for pos, _ in board():
                var = board.get_variable(pos)
                if var is None:
                    continue

                # 右上和右下位置
                up_right = pos.right().up()
                down_right = pos.right().down()

                if not board.in_bounds(up_right) or not board.in_bounds(down_right):
                    continue
                if up_right not in state or down_right not in state:
                    continue

                # 如果当前是水平，且右上和右下都有雷，则它们必须是斜向（2和3）
                # 即：state[pos] == 1  => (state[up_right] == 2 且 state[down_right] == 3)
                # 或者 (state[up_right] == 3 且 state[down_right] == 2)
                is_split = model.NewBoolVar(f"split_{pos}")
                split_cond_1 = model.NewBoolVar(f"split_cond1_{pos}")
                split_cond_2 = model.NewBoolVar(f"split_cond2_{pos}")

                model.Add(state[up_right] == 2).OnlyEnforceIf([split_cond_1, s])
                model.Add(state[down_right] == 3).OnlyEnforceIf([split_cond_1, s])

                model.Add(state[up_right] == 3).OnlyEnforceIf([split_cond_2, s])
                model.Add(state[down_right] == 2).OnlyEnforceIf([split_cond_2, s])

                model.AddBoolOr([split_cond_1, split_cond_2]).OnlyEnforceIf([is_split, s])
                model.AddBoolAnd([split_cond_1.Not(), split_cond_2.Not()]).OnlyEnforceIf([is_split.Not(), s])

                # 如果当前是水平，则可以是分裂点（不强制，因为水平路径可以继续水平）
                # 但如果是分裂点，则右上和右下必须是斜向
                state_is_1_split = model.NewBoolVar(f"state_is_1_split_{pos}")
                model.Add(state[pos] == 1).OnlyEnforceIf([state_is_1_split, s])
                model.Add(state[pos] != 1).OnlyEnforceIf([state_is_1_split.Not(), s])
                model.Add(is_split == 1).OnlyEnforceIf([var, state_is_1_split, split_cond_1, s])

            # ---------- 7. 左边界起始约束 ----------
            # 第一列必须有雷（桥从左边界发出）
            first_col_pos = boundary.left(0)
            first_col_cells = board.get_col_pos(first_col_pos)
            first_col_vars = [
                board.get_variable(p) for p in first_col_cells
                if board.get_variable(p) is not None
            ]
            if first_col_vars:
                model.Add(sum(first_col_vars) >= 1).OnlyEnforceIf(s)

            # 第一列的雷必须是水平或斜向（不能是从左侧来的斜向）
            for pos in first_col_cells:
                var = board.get_variable(pos)
                if var is None:
                    continue
                # 状态必须为1（水平）或2（右上）或3（右下）
                model.Add(state[pos] >= 1).OnlyEnforceIf([var, s])

            # ---------- 8. 右边界终止约束 ----------
            # 最后一列的雷必须停止（不能继续向右）
            last_col_pos = boundary.left(cols - 1)
            last_col_cells = board.get_col_pos(last_col_pos)
            for pos in last_col_cells:
                var = board.get_variable(pos)
                if var is None:
                    continue
                # 右侧不能有雷（已经到边界了）
                # 但状态可以是水平或斜向，因为桥在边界停止
                # 这里不额外约束，因为边界外没有格子
                pass

            # ---------- 9. 上下边界停止约束 ----------
            # 斜向桥遇到上下边界时停止
            # 即：如果某个雷在边界行，其状态不能是向外的斜向
            # 顶部行：状态不能是右上(2)（因为会越界）
            # 底部行：状态不能是右下(3)（因为会越界）
            top_row_pos = boundary.up(rows - 1)  # 实际是行0
            bottom_row_pos = boundary.down(rows - 1)  # 实际是行rows-1

            # 顶部行：不能有状态2（右上）
            for pos in board.get_row_pos(top_row_pos):
                var = board.get_variable(pos)
                if var is None:
                    continue
                model.Add(state[pos] != 2).OnlyEnforceIf([var, s])

            # 底部行：不能有状态3（右下）
            for pos in board.get_row_pos(bottom_row_pos):
                var = board.get_variable(pos)
                if var is None:
                    continue
                model.Add(state[pos] != 3).OnlyEnforceIf([var, s])

    def suggest_total(self, info: dict) -> None:
        """
        建议雷总数：根据题板尺寸和桥的宽度特性，建议总雷数为列数的倍数。
        """
        size_list = [info["size"][key] for key in info["interactive"]]

        def add_hard_constraint(model: cp_model.CpModel, total: cp_model.IntVar) -> None:
            nonlocal size_list
            var_list = []
            for i, (height, width) in enumerate(size_list):
                # 每列雷数相同，所以总雷数 = 列数 * 每列雷数
                # 每列雷数至少为1（从左边界发出）
                n = model.NewIntVar(1, height, f"col_mines_{i}")
                # 总雷数 = 列数 * 每列雷数
                model.Add(total == sum(n for _ in range(width)))
                var_list.append(n)
            # 总雷数在合理范围内
            model.Add(total >= len(size_list))  # 至少每个题板有一个雷

        # 软约束：建议总雷数在 (宽*高) 的 20%~40% 之间
        ub = 0
        for key in info["interactive"]:
            total = info["total"][key]
            ub += total

        info["soft_fn"](ub * 0.25, ub * 0.35)
        info["hard_fns"].append(add_hard_constraint)


def _get_index(a: List[cp_model.IntVar], model: cp_model.CpModel, name: str = "") -> List[cp_model.IntVar]:
    """
    辅助函数：将一维布尔变量数组转换为索引数组。
    参考 2B.py 中的 _get_index 实现。

    输入：a 是布尔变量列表（表示雷的位置）
    输出：b 是整数变量列表，b[i] 表示第 i+1 个 1 的索引位置
    """
    n = len(a)

    # 1. 创建前缀和数组 s
    s = [model.NewIntVar(0, n, f's_{name}_{j}') for j in range(n + 1)]
    model.Add(s[0] == 0)
    for j in range(n):
        model.Add(s[j + 1] == s[j] + a[j])

    # 2. 创建目标输出数组 b
    b = [model.NewIntVar(0, n, f'b_{name}_{i}') for i in range(n)]

    # 3. 建立对偶映射
    for j in range(n):
        model.AddElement(s[j], b, j).OnlyEnforceIf(a[j])

    # 4. 处理数量不足时的边界情况
    for i in range(n - 1):
        model.Add(b[i + 1] >= b[i])

    return b
