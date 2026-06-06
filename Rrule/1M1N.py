"""
[1M1N] 多雷 + 负雷
"""
from ....abs.Rrule import AbstractClueRule, AbstractClueValue

from minesweepervariants.board import Position, Board, JSONObject
from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue
from ....utils.tool import get_logger

class Rule1M1N(AbstractClueRule):
    id = "1M1N"
    name = "Multiple + Negative"
    name.zh_CN = "多雷 + 负雷"
    doc = ""

    tags = ["Meta", "Local", "Number Clue", "Parameter"]
    creation_time = "2025-08-23"
    author = ("", 0)

    def clue_class(self):
        return Value1M1N

    def fill(self, board: 'Board') -> 'Board':
        logger = get_logger()
        for pos, _ in board("N"):
            dyed = undyed = 0
            nei = pos.neighbors(2)
            for t, d in zip(board.batch(nei, mode="type"), board.batch(nei, mode="dye")):
                if (t != "F"):
                    continue
                if d:
                    dyed += 2
                else:
                    undyed += 1
            obj = Value1M1N(pos, abs(dyed - undyed))
            board.set_value(pos, obj)
            logger.debug(f"[1M1N]: put {obj} to {pos}")
        return board


class Value1M1N(AbstractClueValue):
    id = Rule1M1N.id

    def __init__(self, pos: 'Position', value: int, *args: object, **kwargs: object):
        super().__init__(pos, value, *args, **kwargs)
        self.value: SingleIntValue = SingleIntValue(value)
        self.pos = pos

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
        return self.pos.neighbors(2)

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)

        nei_a = [_pos for _pos in self.pos.neighbors(2) if board.get_dyed(_pos)] * 2
        nei_b = [_pos for _pos in self.pos.neighbors(2) if not board.get_dyed(_pos)]

        vars_a = board.batch(nei_a, mode="variable", drop_none=True)
        vars_b = board.batch(nei_b, mode="variable", drop_none=True)

        diff = sum(vars_a) - sum(vars_b)

        # 估计最大绝对值可能为 len(vars_a) + len(vars_b)
        max_abs = len(vars_a) + len(vars_b)
        abs_diff = model.NewIntVar(0, max_abs, "abs_diff")

        model.AddAbsEquality(abs_diff, diff)
        model.Add(abs_diff == self.value.value).OnlyEnforceIf(s)