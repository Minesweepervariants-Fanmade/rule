"""
[1N1X] 负雷 + 十字
"""
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition
from ....utils.tool import get_logger

def cross_neighbors(pos : AbstractPosition) -> list[AbstractPosition]:
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
    name = ["1N1X", "NX", "负雷 + 十字", "Negative + Cross"]
    doc = ""

    def clue_class(self):
        return Value1N1X

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        logger = get_logger()
        for pos, _ in board("N"):
            value = sum(board.get_type(_pos) == "F" if
                        board.get_dyed(_pos)
                        else -(board.get_type(_pos) == "F")
                        for _pos in cross_neighbors(pos))
            obj = Value1N1X(pos, bytes([abs(value)]))
            board.set_value(pos, obj)
            logger.debug(f"[1N1X]: put {abs(value)} to {pos}")
        return board


class Value1N1X(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        self.value = code[0]
        self.nei = cross_neighbors(pos)
        self.pos = pos

    def __repr__(self) -> str:
        return str(self.value)

    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        return self.nei

    @classmethod
    def type(cls) -> bytes:
        return Rule1N1X.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints(self, board: 'AbstractBoard', switch):
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
        model.Add(abs_diff == self.value).OnlyEnforceIf(s)