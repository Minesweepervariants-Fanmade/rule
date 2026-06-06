"""
[1N1X] 负雷 + 十字
"""
from ....abs.Rrule import AbstractClueRule, AbstractClueValue

from minesweepervariants.board import Position, Board, JSONObject
from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue
from ....utils.tool import get_logger


def cross_neighbors(pos : Position) -> list[Position]:
    return [
        pos.up(2),
        pos.down(2),
        pos.left(2),
        pos.right(2),
        pos.up(1),
        pos.down(1),
        pos.left(1),
        pos.right(1)
    ]


class Rule1N1X(AbstractClueRule):
    id = "1N1X"
    name = "Negative + Cross"
    name.zh_CN = "负雷 + 十字"
    doc = ""

    tags = ["Meta", "Local", "Number Clue", "Dyed"]
    creation_time = "2025-08-23"
    author = ("", 0)

    def clue_class(self):
        return Value1N1X

    def fill(self, board: 'Board') -> 'Board':
        logger = get_logger()
        for pos, _ in board("N"):
            value = sum(board.get_type(_pos) == "F" if
                        board.get_dyed(_pos)
                        else -(board.get_type(_pos) == "F")
                        for _pos in cross_neighbors(pos))
            obj = Value1N1X(pos, abs(value))
            board.set_value(pos, obj)
            logger.debug(f"[1N1X]: put {abs(value)} to {pos}")
        return board


class Value1N1X(AbstractClueValue):
    id = "1N1X"

    def __init__(self, pos: 'Position', value: int, *args: object, **kwargs: object):
        super().__init__(pos, value, *args, **kwargs)
        self.value: SingleIntValue = SingleIntValue(value)
        self.pos = pos
        self.nei = cross_neighbors(pos)

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)

        if not is_value_template(_data):
            raise TypeError("value is not template")

        template_data = cast(Template, _data)
        value = SingleIntValue.try_from(template_data)

        if value is None:
            raise ValueError("value is empty")

        return cls(pos, value.value)

    def high_light(self, board: 'Board') -> list['Position']:
        return self.nei

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)

        nei_a = [_pos for _pos in self.nei if board.get_dyed(_pos)]
        nei_b = [_pos for _pos in self.nei if not board.get_dyed(_pos)]

        vars_a = board.batch(nei_a, mode="variable", drop_none=True)
        vars_b = board.batch(nei_b, mode="variable", drop_none=True)

        diff = sum(vars_a) - sum(vars_b)

        # 估计最大绝对值可能为 len(vars_a) + len(vars_b)
        max_abs = len(vars_a) + len(vars_b)
        abs_diff = model.NewIntVar(0, max_abs, "abs_diff")

        model.AddAbsEquality(abs_diff, diff)
        model.Add(abs_diff == self.value.value).OnlyEnforceIf(s)