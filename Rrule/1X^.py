"""
[1X^] 菱形：线索表示距离为 √2 和距离为 2 区域的总雷数
"""

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue
from minesweepervariants.board import JSONObject, Board, Position

from ....utils.tool import get_logger
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG


class Rule1Xr(AbstractClueRule):
    id = "1X^"
    aliases = ("X^",)
    name = "Rhombus"
    name.zh_CN = "菱形"
    doc = "Clue shows the total number of mines at distance √2 and distance 2"
    doc.zh_CN = "线索表示距离为 √2 和距离为 2 区域的总雷数"
    tags = ["Local", "Number Clue", "Vanilla Variant", "Creative"]
    creation_time = "2025-08-24"
    author = ("", 0)

    def fill(self, board: 'Board') -> 'Board':
        logger = get_logger()
        for pos, _ in board("N"):
            value = len([_pos for _pos in pos.neighbors(2, 4) if board.get_type(_pos) == "F"])
            board.set_value(pos, Value1Xr(pos, value))
            logger.debug(f"Set {pos} to 1X^[{value}]")
        return board


class Value1Xr(AbstractClueValue):
    id = Rule1Xr.id

    def __init__(self, pos: 'Position', value: int, *args: object, **kwargs: object):
        super().__init__(pos, value, *args, **kwargs)
        self.value: SingleIntValue = SingleIntValue(value)
        self.count = value
        self.pos = pos
        self.neighbor = pos.neighbors(2, 4)

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
        return self.neighbor

    @classmethod
    def type(cls) -> bytes:
        return Rule1Xr.id.encode("ascii")

    def code(self) -> bytes:
        return bytes([self.count])

    def deduce_cells(self, board: 'Board') -> bool:
        type_dict = {"N": [], "F": []}
        for pos in self.neighbor:
            t = board.get_type(pos)
            if t in ("", "C"):
                continue
            type_dict[t].append(pos)
        n_num = len(type_dict["N"])
        f_num = len(type_dict["F"])
        if n_num == 0:
            return False
        if f_num == self.count:
            for i in type_dict["N"]:
                board.set_value(i, VALUE_QUESS)
            return True
        if f_num + n_num == self.count:
            for i in type_dict["N"]:
                board.set_value(i, MINES_TAG)
            return True
        return False

    def create_constraints(self, board: 'Board', switch):
        """创建CP-SAT约束：周围雷数等于count"""
        model = board.get_model()
        s = switch.get(model, self)
        model.Add(sum(board.batch(self.neighbor, mode="variable", drop_none=True)) == self.count).OnlyEnforceIf(s)
