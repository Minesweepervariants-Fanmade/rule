"""
[3K] 三消：所有四连通雷区域的面积至少为3
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ortools.sat.python.cp_model import CpModel, IntVar

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from .connect import connect

if TYPE_CHECKING:
    from minesweepervariants.impl.summon.solver import Switch


class Rule3K(AbstractMinesRule):
    """三消规则：每个四连通雷区域的面积至少为3。"""

    id = "3K"
    name = "3K"
    name.zh_CN = "三消"
    doc = "Every 4-connected mine region has area at least 3"
    doc.zh_CN = "所有四连通雷区域的面积至少为3"

    tags = ["Variant", "Connectivity", "Construction"]
    creation_time = "2026-09-05"
    author = ("NT", 2201963934)

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        """添加 CP-SAT 约束，确保每个雷连通块的大小 ≥ 3。"""
        model = board.get_model()
        s = switch.get(model, self)

        # 收集所有位置及其雷变量（raw 命名空间）
        positions_vars = [(pos, var) for pos, var in board(mode="var", special='raw')]
        if not positions_vars:
            return

        n = len(positions_vars)
        pos_list = [pos for pos, _ in positions_vars]
        var_list = [var for _, var in positions_vars]

        # 为每个位置创建根变量（表示该位置是否为对应连通块的根）
        root_vars = [model.new_bool_var(f"root_{i}") for i in range(n)]

        # 调用 connect 函数，获取每个位置所属的连通块 ID（根索引）
        component_ids = connect(
            model=model,
            board=board,
            switch=s,
            component_num=None,      # 不限制连通块数量
            connect_value=1,         # 雷连通
            nei_value=1,             # 四连通
            root_vars=root_vars,
            positions_vars=positions_vars,
            special='raw'
        )

        # 为每个可能的根（连通块）创建大小变量
        size_vars = [model.new_int_var(0, n, f"size_{i}") for i in range(n)]

        for i in range(n):
            # 收集属于连通块 i 的成员（且为雷）
            member_vars = []
            for j in range(n):
                # 判断 component_ids[j] == i
                eq = model.new_bool_var(f"eq_{j}_{i}")
                model.add(component_ids[j] == i).only_enforce_if(eq)
                model.add(component_ids[j] != i).only_enforce_if(eq.Not())

                # 成员 = eq 且 var_list[j] == 1
                member = model.new_bool_var(f"member_{j}_{i}")
                model.add(member <= eq).only_enforce_if(s)
                model.add(member <= var_list[j]).only_enforce_if(s)
                model.add(member >= eq + var_list[j] - 1).only_enforce_if(s)

                member_vars.append(member)

            # 大小 = 所有成员之和
            model.add(size_vars[i] == sum(member_vars)).only_enforce_if(s)

            # 如果该连通块存在（root_vars[i] 为真），则其大小必须 ≥ 3
            model.add(size_vars[i] >= 3).only_enforce_if([root_vars[i], s])

    def suggest_total(self, info: dict) -> None:
        """提供总雷数的软约束建议，使密度适中（约 35%）。"""
        ub = 0
        for key in info["interactive"]:
            total_cells = info["total"][key]
            ub += total_cells
        # 建议总雷数约为总格子数的 35%
        info["soft_fn"](int(ub * 0.35), 0)
