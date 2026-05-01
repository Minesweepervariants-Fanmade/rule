#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/04/09
# @Author  : NT (2201963934)
# @FileName: MB.py
"""
[MB] 平衡点：所有雷的平均位置是整点

规则拆分定义（验收基线）
1) 规则对象与适用范围
- 规则对象: 左线规则（Lrule, 雷布局全局约束）。
- 作用对象: 同一交互棋盘 key 下的全部雷变量。
- 重要: 该规则无 fill 阶段，仅在 create_constraints 中建模。

2) 核心术语定义
- 雷集合 M: 该棋盘 key 下所有为雷的格子集合，N = |M|。
- 平均位置(质心):
    mu_x = sum(x_i) / N, mu_y = sum(y_i) / N。
- 整点条件:
    mu_x 与 mu_y 同时为整数。
- 等价约束:
    存在整数 kx, ky 使 sum(x_i) = N * kx 且 sum(y_i) = N * ky。

3) 计数对象、边界与越界
- 计数对象: N、sum_x、sum_y 三个全局量。
- 边界格处理: 与其他格一致，仅由坐标参与求和。
- 越界处理: 不涉及越界候选，统计域固定为棋盘内变量。

4) 语义等价关系
- 定义语义: “所有雷平均位置是整点”。
- 约束语义: 通过整数乘法等式表达可整除性，与定义语义等价。
- 与总雷数规则 R 的关系:
    当用户显式给出 -t 时，必须与 MB 约束兼容，不得系统性导致“左线/雷数矛盾”。

5) 可验证样例
- 样例A(应满足): 雷在 (1,1),(1,3),(3,1),(3,3)，质心 (2,2) 为整点。
- 样例B(应不满足): 雷在 (0,0),(0,1)，质心 (0,0.5) 非整点。

6) 验收要点
- `poetry run python -m py_compile` 无语法错误。
- `-s 5 -c MB -a 1 --seed 42` 不应直接出现“左线/雷数矛盾”。
- `-s 5 -c MB -r -a 20 -t 4` 不应高频全失败为同一矛盾原因。
"""

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class RuleMB(AbstractMinesRule):
    id = "MB"
    name = "Mass-Balance"
    name.zh_CN = "平衡点"
    doc = "The average position of all mines is an integer point"
  doc.zh_CN = "所有雷的平均位置是整点"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            positions = [pos for pos, _ in board(key=key)]
            if not positions:
                continue

            mines = [board.get_variable(pos, special="raw") for pos in positions]
            cell_count = len(positions)

            xs = [pos.x for pos in positions]
            ys = [pos.y for pos in positions]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)

            n = model.NewIntVar(0, cell_count, f"MB_n_{key}")

            sum_x_lb = sum(x for x in xs if x < 0)
            sum_x_ub = sum(x for x in xs if x > 0)
            sum_y_lb = sum(y for y in ys if y < 0)
            sum_y_ub = sum(y for y in ys if y > 0)
            sum_x = model.NewIntVar(sum_x_lb, sum_x_ub, f"MB_sum_x_{key}")
            sum_y = model.NewIntVar(sum_y_lb, sum_y_ub, f"MB_sum_y_{key}")

            model.Add(n == sum(mines)).OnlyEnforceIf(s)
            model.Add(sum_x == sum(pos.x * mine for pos, mine in zip(positions, mines))).OnlyEnforceIf(s)
            model.Add(sum_y == sum(pos.y * mine for pos, mine in zip(positions, mines))).OnlyEnforceIf(s)

            # n=0 时质心未定义，这里按 vacuous true 处理，不额外限制。
            has_mine = model.NewBoolVar(f"MB_has_mine_{key}")
            model.Add(n >= 1).OnlyEnforceIf([s, has_mine])
            model.Add(n == 0).OnlyEnforceIf([s, has_mine.Not()])

            count_selectors = []
            for count in range(1, cell_count + 1):
                is_count = model.NewBoolVar(f"MB_n_is_{count}_{key}")
                count_selectors.append(is_count)

                model.Add(n == count).OnlyEnforceIf([s, is_count])
                model.Add(n != count).OnlyEnforceIf([s, is_count.Not()])

                kx_count = model.NewIntVar(min_x, max_x, f"MB_kx_{count}_{key}")
                ky_count = model.NewIntVar(min_y, max_y, f"MB_ky_{count}_{key}")

                # 在固定 n=count 的分支里，sum_x/sum_y 必须是 count 的整倍数。
                model.Add(sum_x == count * kx_count).OnlyEnforceIf([s, is_count])
                model.Add(sum_y == count * ky_count).OnlyEnforceIf([s, is_count])

            model.Add(sum(count_selectors) == 1).OnlyEnforceIf([s, has_mine])
            model.Add(sum(count_selectors) == 0).OnlyEnforceIf([s, has_mine.Not()])
