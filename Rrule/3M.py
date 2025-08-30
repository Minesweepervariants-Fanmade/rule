"""
[3M]对映：线索表示周围八格组成四个正好相对的组合中有且仅有一个是雷的数量（题板外视为非雷）
"""

from ....abs.board import AbstractBoard, AbstractPosition
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....utils.tool import get_logger
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG

offsets = [
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 1),
    (1, -1),
    (1, 0),
    (1, 1)
]


class Rule3M(AbstractClueRule):
    name = ["3M", "对映", "Mirror"]
    doc = "线索表示周围八格组成四个正好相对的格子组有且仅有一个是雷的组数（题板外视为非雷）"

    logger = get_logger()

    def fill(self, board: AbstractBoard) -> AbstractBoard:
        logger = get_logger()
        for pos, _ in board("N"):
            temp = []
            for x, y in offsets:
                temp.append(board.get_type(pos.shift(x, y)) == "F")
            value = sum(1 for i in range(4) if temp[i] != temp[7 - i])
            board.set_value(pos, Value3M(pos, count=value))
            logger.debug(f"Set value for {pos}: 3M[{value}]")
        return board

class Value3M(AbstractClueValue):
    def __init__(self, pos: AbstractPosition, count: int = 0, code: bytes = None):
        super().__init__(pos, code)
        if code is not None:
            # 从字节码解码
            self.count = code[0]
        else:
            # 直接初始化
            self.count = count
        self.neighbor = self.pos.neighbors(2)

    def __repr__(self):
        return f"{self.count}"

    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        return self.neighbor

    @classmethod
    def type(cls) -> bytes:
        return Rule3M.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.count])

    def invalid(self, board: 'AbstractBoard') -> bool:
        return board.batch(self.neighbor, mode="type").count("N") == 0

    def deduce_cells(self, board: 'AbstractBoard') -> bool:
        types = []
        for x, y in offsets:
            type_obj = board.get_type(self.pos.shift(x, y))
            if type_obj == "C" or type_obj == "":
                types.append(-1)
            elif type_obj == "F":
                types.append(1)
            else:
                types.append(2)
        defined = 0
        can_be_deduced = []
        for i in range(4):
            if types[i] + types[7 - i] == 0:
                defined += 1
            elif types[i] == 2 and types[7 - i] != 2:
                can_be_deduced.append(i)
            elif types[i] != 2 and types[7 - i] == 2:
                can_be_deduced.append(7 - i)
        if defined == self.count:
            for i in can_be_deduced:
                offsetX, offsetY = offsets[i]
                mirrorType = board.get_type(self.pos.shift(-offsetX, -offsetY))
                if mirrorType == "C" or mirrorType == "":
                    board.set_value(self.pos.shift(offsetX, offsetY), VALUE_QUESS)
                elif mirrorType == "F":
                    board.set_value(self.pos.shift(offsetX, offsetY), MINES_TAG)
            return True
        elif defined + len(can_be_deduced) == self.count:
            for i in can_be_deduced:
                offsetX, offsetY = offsets[i]
                mirrorType = board.get_type(self.pos.shift(-offsetX, -offsetY))
                if mirrorType == "C" or mirrorType == "":
                    board.set_value(self.pos.shift(offsetX, offsetY), MINES_TAG)
                elif mirrorType == "F":
                    board.set_value(self.pos.shift(offsetX, offsetY), VALUE_QUESS)
            return True
        return False

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()

        g1 = model.NewBoolVar("3M_g1")
        g2 = model.NewBoolVar("3M_g2")
        g3 = model.NewBoolVar("3M_g3")
        g4 = model.NewBoolVar("3M_g4")

        s = switch.get(model, self)

        model.Add(sum(board.batch([self.pos.shift(-1, -1), self.pos.shift(1, 1)], mode="variable",
                                  drop_none=True)) == 1).OnlyEnforceIf([g1, s])
        model.Add(sum(board.batch([self.pos.shift(-1, -1), self.pos.shift(1, 1)], mode="variable",
                                  drop_none=True)) != 1).OnlyEnforceIf([g1.Not(), s])

        model.Add(sum(board.batch([self.pos.shift(-1, 0), self.pos.shift(1, 0)], mode="variable",
                                  drop_none=True)) == 1).OnlyEnforceIf([g2, s])
        model.Add(sum(board.batch([self.pos.shift(-1, 0), self.pos.shift(1, 0)], mode="variable",
                                  drop_none=True)) != 1).OnlyEnforceIf([g2.Not(), s])

        model.Add(sum(board.batch([self.pos.shift(-1, 1), self.pos.shift(1, -1)], mode="variable",
                                  drop_none=True)) == 1).OnlyEnforceIf([g3, s])
        model.Add(sum(board.batch([self.pos.shift(-1, 1), self.pos.shift(1, -1)], mode="variable",
                                  drop_none=True)) != 1).OnlyEnforceIf([g3.Not(), s])

        model.Add(sum(board.batch([self.pos.shift(0, -1), self.pos.shift(0, 1)], mode="variable",
                                  drop_none=True)) == 1).OnlyEnforceIf([g4, s])
        model.Add(sum(board.batch([self.pos.shift(0, -1), self.pos.shift(0, 1)], mode="variable",
                                  drop_none=True)) != 1).OnlyEnforceIf([g4.Not(), s])

        model.Add(sum([g1, g2, g3, g4]) == self.count).OnlyEnforceIf(s)
