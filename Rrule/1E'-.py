from ortools.sat.python.cp_model import IntVar

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition



class Rule1E(AbstractClueRule):
    id = "1E'-"
    name = "Eyesight'-"
    name.zh_CN = "视差'-"  # pyright: ignore[reportAttributeAccessIssue]
    doc = "Clue shows the difference between vertical and horizontal eyesight."
    doc.zh_CN = "视差-: 线索表示纵向和横向的视野之差。"  # pyright: ignore[reportAttributeAccessIssue]
    tags = ["Local", "Number Clue", "Arrow Clue", "Extensive Trial", "Creative"]
    creation_time = "2026-05-30"
    author = ("NT", 2201963934)

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
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

            board.set_value(pos, Value1E(pos, bytes([value])))
        return board


def get_line(board: 'AbstractBoard', pos: 'AbstractPosition', direction: str) -> list['AbstractPosition']:
    line: list['AbstractPosition'] = []
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
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        self.value = code[0]
        self.pos = pos

    def __repr__(self):
        return str(self.value)

    @classmethod
    def type(cls) -> bytes:
        return b"1E'"

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints(self, board: 'AbstractBoard', switch):
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

        model.add_abs_equality(self.value, (horizontal - vertical)).OnlyEnforceIf(s)