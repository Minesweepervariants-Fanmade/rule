"""
[1K]骑士:每个位置代表其马步位置格子的总雷值
"""

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Position, Board, JSONObject
from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue


class Rule1K(AbstractClueRule):
    id = "1K"
    aliases = ("K",)
    name = "Knight"
    name.zh_CN = "骑士"
    doc = "Clue indicates the total mine value at the eight knight's move positions"
    doc.zh_CN = "线索表示马步位置 8 个格子中的总雷值"
    tags = ["Original", "Local", "Number Clue"]
    creation_time = "2025-08-06"
    author = ("", 0)

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        self.rule = data or "raw"

    def fill(self, board: 'Board') -> 'Board':
        for pos, _ in board("N", special='raw'):
            value = board.batch(pos.neighbors(5, 5), "type", special=self.rule)
            value = value.count("F")
            board.set_value(pos, Value1K(pos, value=value, rule=self.rule))
        return board

    def get_deps(self) -> list[str]:
        if self.rule == 'raw':
            return []
        return [self.rule]


class Value1K(AbstractClueValue):
    id = Rule1K.id

    def __init__(self, pos: 'Position', value: int, rule, *args: object, **kwargs: object):
        super().__init__(pos, value, *args, **kwargs)
        self.value: SingleIntValue = SingleIntValue(value)
        self.pos = pos
        self.rule = rule

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)

        if not is_value_template(_data):
            raise TypeError("value is not template")

        template_data = cast(Template, _data)
        value = SingleIntValue.try_from(template_data)

        if value is None:
            raise ValueError("value is empty")

        return cls(pos, value.value, _data.get("rule", "raw"))

    def create_constraints(self, board: 'Board', switch):
        """创建CP-SAT约束: 周围雷数等于count"""
        model = board.get_model()

        # 收集周围格子的布尔变量
        neighbor_vars = []
        for neighbor in self.pos.neighbors(5, 5):  # 8方向相邻格子
            if board.in_bounds(neighbor):
                var = board.get_variable(neighbor, special=self.rule)
                neighbor_vars.append(var)

        # 添加约束：周围雷数等于count
        if neighbor_vars:
            model.Add(sum(neighbor_vars) == self.value.value).OnlyEnforceIf(switch.get(model, self.pos))
