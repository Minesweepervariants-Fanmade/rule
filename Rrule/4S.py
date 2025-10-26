"""
[4S] 阶梯：所有雷被视为 X 个雷（X 为其的行列数之和）
"""

from ....abs.board import AbstractBoard, AbstractPosition
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....utils.tool import get_logger
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG


def encode_int_7bit(n: int) -> bytes:
    # 编码主体：每7位 -> 1字节（bit6~bit0，bit7=0）
    if n == 0:
        return b'\x00'
    payload = []

    while n > 0:
        payload.append(n & 0x7f)
        n >>= 7

    return bytes(payload)


def decode_bytes_7bit(data: bytes) -> int:
    if len(data) == 0:
        return 0

    result = 0
    for i in data[::-1]:
        result <<= 7
        result |= i

    return result

class Rule4S(AbstractClueRule):
    name = ["4S", "阶梯", "Staircase"]
    doc = "所有雷被视为 X 个雷（X 为其的行列数之和）"

    def fill(self, board: AbstractBoard) -> AbstractBoard:
        logger = get_logger()
        for pos, _ in board("N"):
            positions = pos.neighbors(2)
            value = sum(p.x + p.y + 2 for p in positions if board.get_type(p) == "F")
            board.set_value(pos, Value4S(pos, code=encode_int_7bit(value)))
        return board

class Value4S(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        super().__init__(pos)
        self.value = decode_bytes_7bit(code)
        self.neighbors = pos.neighbors(2)

    def __repr__(self) -> str:
        return f"{self.value}"

    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        return self.neighbors

    @classmethod
    def type(cls) -> bytes:
        return Rule4S.name[0].encode("ascii")

    def code(self) -> bytes:
        return encode_int_7bit(self.value)
    
    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        var_list = [board.get_variable(pos) * (pos.x + pos.y + 2) for pos in self.neighbors if board.in_bounds(pos)]
        model.Add(sum(var_list) == self.value).OnlyEnforceIf(s)
