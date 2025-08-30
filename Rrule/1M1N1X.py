"""
[1M1N] 多雷 + 负雷 + 十字
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

class Rule1M1N1X(AbstractClueRule):
    name = ["1M1N1X", "MNX", "多雷 + 负雷 + 十字", "Multiple + Negative + Cross"]
    doc = ""

    def clue_class(self):
        return Value1M1N1X

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        logger = get_logger()
        for pos, _ in board("N"):
            dyed = undyed = 0
            nei = cross_neighbors(pos)
            for t, d in zip(board.batch(nei, mode="type"), board.batch(nei, mode="dye")):
                if (t != "F"):
                    continue
                if d:
                    dyed += 2
                else:
                    undyed += 1
            obj = Value1M1N1X(pos, bytes([abs(dyed - undyed)]))
            board.set_value(pos, obj)
            logger.debug(f"[1M1N]: put {obj} to {pos}")
        return board
    
class Value1M1N1X(AbstractClueValue):
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
        return Rule1M1N1X.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])
    
    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        nei_a = [_pos for _pos in self.nei if board.get_dyed(_pos)] * 2
        nei_b = [_pos for _pos in self.nei if not board.get_dyed(_pos)]

        vars_a = board.batch(nei_a, mode="variable", drop_none=True)
        vars_b = board.batch(nei_b, mode="variable", drop_none=True)

        diff = sum(vars_a) - sum(vars_b)

        # 估计最大绝对值可能为 len(vars_a) + len(vars_b)
        max_abs = len(vars_a) + len(vars_b)
        abs_diff = model.NewIntVar(0, max_abs, "abs_diff")

        model.AddAbsEquality(abs_diff, diff)
        model.Add(abs_diff == self.value).OnlyEnforceIf(s)