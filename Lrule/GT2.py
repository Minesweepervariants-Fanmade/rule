"""
[GT2] 所有四连通雷/非雷区域面积大于 2。

参数化语义:
- 默认时，所有四连通雷/非雷区域面积都至少为 3。
- 传入 data 后，可通过前缀定向控制目标区域：
    - `#` 前缀仅作用于雷区域，例如 `#1..4`。
    - `?` 前缀仅作用于非雷区域，例如 `?1..4`。
    - 无前缀子句默认同时作用于雷区域与非雷区域。
- data 支持区间串与组合串，例如 "1..2"、"..5"、"1.."，其中 `..` 表示左右端点都包含。
- 组合语义为 AND，同一连通块面积必须同时满足所有子条件。
- data 为空字符串时，等价于未传参数，保留默认语义，不应报错。
"""

from __future__ import annotations

import re

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard

from .connect import connect


class RuleGT2(AbstractMinesRule):
    id = "GT2"
    name = "Greater Than 2"
    name.zh_CN = "大于 2"
    doc = "All four-connected mine/non-mine areas have size greater than 2"
    doc.zh_CN = "所有四连通雷/非雷区域面积大于 2"
    author = ("NT", 2201963934)
    tags = ["Original", "Global", "Connectivity", "Construction", "Parameter"]

    _COMPARATOR_RE = re.compile(r"^(>=|<=|!=|>|<)\s*(-?\d+)$")

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        self.mine_area_conditions, self.safe_area_conditions = self._parse_data(data)

    @staticmethod
    def _parse_int(text: str, raw_data: str) -> int:
        try:
            return int(text)
        except ValueError as exc:
            raise ValueError(f"GT2 data 数值非法: {raw_data!r}") from exc

    @classmethod
    def _parse_interval_clause(cls, item: str, raw_data: str) -> list[tuple[str, int]] | None:
        if ".." not in item:
            return None

        if item.count("..") != 1:
            raise ValueError(f"GT2 data 区间子句非法: {raw_data!r}")

        left, right = item.split("..", 1)
        left = left.strip()
        right = right.strip()

        if not left and not right:
            raise ValueError(f"GT2 data 区间子句不能为空: {raw_data!r}")

        conditions: list[tuple[str, int]] = []
        lower = None
        upper = None

        if left:
            lower = cls._parse_int(left, raw_data)
            conditions.append((">=", lower))

        if right:
            upper = cls._parse_int(right, raw_data)
            conditions.append(("<=", upper))

        if lower is not None and upper is not None and lower > upper:
            raise ValueError(f"GT2 data 区间上下界非法: {raw_data!r}")

        return conditions

    @classmethod
    def _parse_data(cls, data) -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
        if data is None:
            return [], []

        if not isinstance(data, str):
            raise ValueError(f"GT2 data 必须是字符串, 但收到: {data!r}")

        text = data.strip()
        if not text:
            return [], []

        mine_conditions: list[tuple[str, int]] = []
        safe_conditions: list[tuple[str, int]] = []
        for part in text.split(","):
            item = part.strip()
            if not item:
                raise ValueError(f"GT2 data 中存在空子句: {data!r}")

            target = "both"
            if item[0] in ("#", "?"):
                target = item[0]
                item = item[1:].strip()
                if not item:
                    raise ValueError(f"GT2 data 子句缺少条件: {data!r}")

            interval_conditions = cls._parse_interval_clause(item, data)
            if interval_conditions is not None:
                if target in ("both", "#"):
                    mine_conditions.extend(interval_conditions)
                if target in ("both", "?"):
                    safe_conditions.extend(interval_conditions)
                continue

            match = cls._COMPARATOR_RE.fullmatch(item)
            if match is None:
                raise ValueError(f"GT2 data 格式非法: {data!r}")

            condition = (match.group(1), int(match.group(2)))
            if target in ("both", "#"):
                mine_conditions.append(condition)
            if target in ("both", "?"):
                safe_conditions.append(condition)

        return mine_conditions, safe_conditions

    def _enforce_min_area(self, model, s, component_ids, root_vars, active_vars, conditions, prefix: str):
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
            for op, value in conditions:
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

            self._enforce_min_area(
                model,
                s,
                mine_component_ids,
                root_mines,
                active_mines,
                self.mine_area_conditions,
                f"gt2_{key}_mine",
            )
            self._enforce_min_area(
                model,
                s,
                safe_component_ids,
                root_safe,
                active_safe,
                self.safe_area_conditions,
                f"gt2_{key}_safe",
            )
