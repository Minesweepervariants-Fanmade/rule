"""
[4Q] 方格：线索表示包含该格且包含雷的 2x2 区域数
"""
from typing import Dict

from minesweepervariants.utils.web_template import MultiNumber
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition
from ....utils.image_create import get_text, get_row

from ....utils.tool import get_logger

class Rule4Q(AbstractClueRule):
    name = ["4Q", "方格"]
    doc = "线索表示包含该格且包含雷的 2x2 区域数"

    def fill(self, board: AbstractBoard) -> AbstractBoard:
        for pos, _ in board("N"):
            grids = [
                [pos.up(), pos.up().left(), pos.left()],
                [pos.down(), pos.down().left(), pos.left()],
                [pos.up(), pos.up().right(), pos.right()],
                [pos.down(), pos.down().right(), pos.right()]
            ]
            value = sum(1 for g in grids if all(board.in_bounds(p) for p in g) and any(board.get_type(p) == 'F' for p in g))
            board.set_value(pos, Value4Q(pos, bytes([value])))

        return board
    
class Value4Q(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        super().__init__(pos)
        self.value = code[0]
        self.neighbors = pos.neighbors(2)
        self.grids = [
            [pos.up(), pos.up().left(), pos.left()],
            [pos.down(), pos.down().left(), pos.left()],
            [pos.up(), pos.up().right(), pos.right()],
            [pos.down(), pos.down().right(), pos.right()]
        ]

    def __repr__(self) -> str:
        return f"{self.value}"
    
    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        return self.neighbors

    @classmethod
    def type(cls) -> bytes:
        return Rule4Q.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])
    
    def create_constraints(self, board: 'AbstractBoard', switch):
        valid_grids = [g for g in self.grids if all(board.in_bounds(p) for p in g)]
        model = board.get_model()
        s = switch.get(model, self)
        vars = [model.NewBoolVar(f"4Q_{i}") for i, g in enumerate(valid_grids)]
        for var, g in zip(vars, valid_grids):
            model.AddBoolOr(board.batch(g, mode="variable")).OnlyEnforceIf(var)
            model.Add(sum(board.batch(g, mode="variable")) == 0).OnlyEnforceIf(var.Not())
        model.Add(sum(vars) == self.value).OnlyEnforceIf(s)
        