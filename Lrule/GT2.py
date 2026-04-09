"""
[GT2] 所有四连通雷/非雷区域面积大于 2。
"""

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard

from .connect import connect


class RuleGT2(AbstractMinesRule):
    name = ["GT2", "所有四连通雷/非雷区域面积大于 2", "GT2"]
    doc = "所有四连通雷/非雷区域面积大于 2"

    def _enforce_min_area(self, model, s, component_ids, root_vars, active_vars, prefix: str):
        n = len(active_vars)
        if n == 0:
            return

        for i in range(n):
            size_var = model.NewIntVar(0, n, f"{prefix}_size_{i}")
            member_flags = []
            for j, active_var in enumerate(active_vars):
                same_component = model.NewBoolVar(f"{prefix}_same_{i}_{j}")
                model.Add(component_ids[j] == i).OnlyEnforceIf([same_component, s])
                model.Add(component_ids[j] != i).OnlyEnforceIf([same_component.Not(), s])

                member = model.NewBoolVar(f"{prefix}_member_{i}_{j}")
                model.Add(member <= same_component).OnlyEnforceIf(s)
                model.Add(member <= active_var).OnlyEnforceIf(s)
                model.Add(member >= same_component + active_var - 1).OnlyEnforceIf(s)
                member_flags.append(member)

            model.Add(size_var == sum(member_flags)).OnlyEnforceIf(s)
            model.Add(size_var >= 3).OnlyEnforceIf([root_vars[i], s])

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            positions_vars = [
                (pos, board.get_variable(pos, special='raw'))
                for pos, _ in board(key=key, mode='variable', special='raw')
            ]
            if not positions_vars:
                continue

            root_mines = [model.NewBoolVar(f"gt2_mine_root_{key}_{i}") for i in range(len(positions_vars))]
            root_safe = [model.NewBoolVar(f"gt2_safe_root_{key}_{i}") for i in range(len(positions_vars))]

            safe_vars = []
            for i, (_, mine_var) in enumerate(positions_vars):
                safe_var = model.NewBoolVar(f"gt2_{key}_safe_var_{i}")
                model.Add(safe_var + mine_var == 1).OnlyEnforceIf(s)
                safe_vars.append(safe_var)

            mine_component_ids = connect(
                model=model,
                board=board,
                switch=s,
                component_num=None,
                connect_value=1,
                nei_value=1,
                positions_vars=positions_vars,
                root_vars=root_mines,
                special='raw',
            )
            safe_component_ids = connect(
                model=model,
                board=board,
                switch=s,
                component_num=None,
                connect_value=0,
                nei_value=1,
                positions_vars=positions_vars,
                root_vars=root_safe,
                special='raw',
            )

            active_mines = [var for _, var in positions_vars]
            active_safe = safe_vars

            self._enforce_min_area(model, s, mine_component_ids, root_mines, active_mines, f"gt2_{key}_mine")
            self._enforce_min_area(model, s, safe_component_ids, root_safe, active_safe, f"gt2_{key}_safe")
