from typing import cast

from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template, Template
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue
from minesweepervariants.board import JSONObject, Board, Position



class Rule1E(AbstractClueRule):
    id = "1E'-"
    name = "Eyesight'-"
    name.zh_CN = "视方差"  # pyright: ignore[reportAttributeAccessIssue]
    doc = "Clue shows the variance of vertical and horizontal sight multiplied by 2 and then take the square root. Or in other words, clue shows the difference between vertical and horizontal sight."
    doc.zh_CN = "视方差: 线索表示纵向和横向的视野之方差乘以2并开根. 或者说线索表示纵向和横向的视野之差。"  # pyright: ignore[reportAttributeAccessIssue]
    tags = ["Local", "Number Clue", "Arrow Clue", "Extensive Trial", "Creative"]
    creation_time = "2026-05-30"
    author = ("NT", 2201963934)

    def fill(self, board: 'Board') -> 'Board':
        for pos, _ in board("N"):
            up = get_line(board, pos, 'up')
            down = get_line(board, pos, 'down')
            left = get_line(board, pos, 'left')
            right = get_line(board, pos, 'right')

            up_vars = [board.get_type(p) == "F" for p in up if board.get_variable(p) is not None] + [True]
            down_vars = [board.get_type(p) == "F" for p in down if board.get_variable(p) is not None] + [True]
            left_vars = [board.get_type(p) == "F" for p in left if board.get_variable(p) is not None] + [True]
            right_vars = [board.get_type(p) == "F" for p in right if board.get_variable(p) is not None] + [True]

            up_count = up_vars.index(True)
            down_count = down_vars.index(True)
            left_count = left_vars.index(True)
            right_count = right_vars.index(True)

            horizontal = abs(left_count + right_count)
            vertical = abs(up_count + down_count)

            value = abs(horizontal - vertical)

            board.set_value(pos, Value1E(pos, value))
        return board


def get_line(board: 'Board', pos: 'Position', direction: str) -> list['Position']:
    line: list['Position'] = []
    while True:
        if direction == 'up':
            next_pos = pos.up()
        elif direction == 'down':
            next_pos = pos.down()
        elif direction == 'left':
            next_pos = pos.left()
        elif direction == 'right':
            next_pos = pos.right()
        else:
            raise ValueError(f"Invalid direction: {direction}")

        if not board.in_bounds(next_pos):
            break
        line.append(next_pos)
        pos = next_pos
    return line


class Value1E(AbstractClueValue):
    id = Rule1E.id

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

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)

        pos = self.pos

        up = get_line(board, pos, 'up')
        down = get_line(board, pos, 'down')
        left = get_line(board, pos, 'left')
        right = get_line(board, pos, 'right')

        up_vars = [v for p in up if (v := board.get_variable(p)) is not None] + [True]
        down_vars = [v for p in down if (v := board.get_variable(p)) is not None] + [True]
        left_vars = [v for p in left if (v := board.get_variable(p)) is not None] + [True]
        right_vars = [v for p in right if (v := board.get_variable(p)) is not None] + [True]

        up_count = model.new_int_var(0, len(up), f"{pos}_up_count")
        down_count = model.new_int_var(0, len(down), f"{pos}_down_count")
        left_count = model.new_int_var(0, len(left), f"{pos}_left_count")
        right_count = model.new_int_var(0, len(right), f"{pos}_right_count")

        def index(idx: IntVar, vars: list[IntVar | bool]):
            model.add_element(idx, vars, 1)
            for i, v in enumerate(vars):
                gt_v = model.new_bool_var(f"{pos}_{idx}_>_{i}")
                model.add(idx > i).OnlyEnforceIf(gt_v)
                model.add(idx <= i).OnlyEnforceIf(gt_v.Not())

                model.add(v == 0).OnlyEnforceIf(gt_v)

        index(up_count, up_vars)
        index(down_count, down_vars)
        index(left_count, left_vars)
        index(right_count, right_vars)

        horizontal = (left_count + right_count)
        vertical = (up_count + down_count)

        model.add_abs_equality(self.value.value, (horizontal - vertical)).OnlyEnforceIf(s)