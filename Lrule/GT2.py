"""
[GT2] 所有四连通雷/非雷区域面积大于 2。

参数化语义:
- 默认时，所有四连通雷/非雷区域面积都至少为 3。
- 传入 data 后，只改变雷区域面积约束；非雷区域仍保持面积至少为 3。
- data 支持比较串与组合串，例如 ">3"、">=2"、"<5"、"<=4"、"!=3"、">5,<=8"、">=2,<5"。
- 组合语义为 AND，同一连通块面积必须同时满足所有子条件。
"""

from __future__ import annotations

import re

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard

from .connect import connect


class RuleGT2(AbstractMinesRule):
    name = ["GT2", "所有四连通雷/非雷区域面积大于 2", "GT2"]
    doc = "所有四连通雷/非雷区域面积大于 2"

    _COMPARATOR_RE = re.compile(r"^(>=|<=|!=|>|<)\s*(-?\d+)$")

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        self.mine_area_conditions: list[tuple[str, int]] = self._parse_data(data)

    @classmethod
    def _parse_data(cls, data) -> list[tuple[str, int]]:
        if data is None:
            return []

        if not isinstance(data, str):
            raise ValueError(f"GT2 data 必须是比较字符串, 但收到: {data!r}")

        text = data.strip()
        if not text:
            return []

        conditions: list[tuple[str, int]] = []
        for part in text.split(","):
            item = part.strip()
            if not item:
                raise ValueError(f"GT2 data 中存在空比较子句: {data!r}")

            match = cls._COMPARATOR_RE.fullmatch(item)
            if match is None:
                raise ValueError(f"GT2 data 格式非法: {data!r}")

            conditions.append((match.group(1), int(match.group(2))))

        return conditions

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
            for op, value in self.mine_area_conditions:
                if op == ">":
                    model.Add(size_var > value).OnlyEnforceIf([root_vars[i], s])
                elif op == ">=":
                    model.Add(size_var >= value).OnlyEnforceIf([root_vars[i], s])
                elif op == "<":
                    model.Add(size_var < value).OnlyEnforceIf([root_vars[i], s])
                elif op == "<=":
                    model.Add(size_var <= value).OnlyEnforceIf([root_vars[i], s])
                elif op == "!=":
                    model.Add(size_var != value).OnlyEnforceIf([root_vars[i], s])
                else:
                    raise ValueError(f"GT2 不支持的比较符号: {op!r}")

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
