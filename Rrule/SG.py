from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition

class RuleSG(AbstractClueRule):
    id = "SG"
    name = "Singleton"
    name.zh_CN = "单一"
    doc = "Clue indicates the sum of rows and columns in the 3x3 area that have exactly one mine"
    doc.zh_CN = "线索表示周围 3x3 范围内恰好只有一雷的行数和列数之和"
    author = ("Boi", -1)
    tags = ["Original", "Local", "Number Clue", "Construction"]

    def fill(self, board: AbstractBoard) -> AbstractBoard:
        for pos, _ in board("N"):
            value = 0
            for i in [-1, 0, 1]:
                if board.batch([pos.up(i).left(), pos.up(i), pos.up(i).right()], mode="type").count("F") == 1:
                    value += 1
                if board.batch([pos.left(i).up(), pos.left(i), pos.left(i).down()], mode="type").count("F") == 1:
                    value += 1
            board.set_value(pos, ValueSG(pos, bytes([value])))
        return board

class ValueSG(AbstractClueValue):
    def __init__(self, pos: AbstractPosition, code: bytes = b''):
        super().__init__(pos, code)
        self.value = code[0]

        self.col_row_poses = []
        for i in [-1, 0, 1]:
            self.col_row_poses.append([pos for pos in [self.pos.up(i).left(), self.pos.up(i), self.pos.up(i).right()]])
            self.col_row_poses.append([pos for pos in [self.pos.left(i).up(), self.pos.left(i), self.pos.left(i).down()]])

    def __repr__(self) -> str:
        return str(self.value)

    @classmethod
    def type(cls) -> bytes:
        return RuleSG.id.encode()

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints(self, board: AbstractBoard, switch):
        model = board.get_model()
        s = switch.get(model, self)

        temp_vars = []
        for poses in self.col_row_poses:
            temp_var = model.NewBoolVar("SG")
            temp_vars.append(temp_var)
            model.Add(sum(board.batch(poses, mode="var", drop_none=True)) == 1).OnlyEnforceIf(temp_var)
            model.Add(sum(board.batch(poses, mode="var", drop_none=True)) != 1).OnlyEnforceIf(temp_var.Not())

        model.Add(sum(temp_vars) == self.value).OnlyEnforceIf(s)
