"""
[2D'']偏移: 线索表示以四方向偏移一格为中心的3x3区域内的雷数最多的区域的雷数
"""

from typing import List
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG

from ....utils.tool import get_logger

class Rule2D(AbstractClueRule):
    name = ["2D''", "偏移''", "Deviation''"]
    doc = "线索表示以四方向偏移一格为中心的3x3区域内的雷数最多的区域的雷数"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        logger = get_logger()
        for pos, _ in board("N"):
            counts = []
            for _pos in [pos.up(1), pos.down(1), pos.right(1), pos.left(1)]:
                count = len([__pos for __pos in _pos.neighbors(0, 2) if board.get_type(__pos) == "F"])
                counts.append(count)
            value = max(counts)
            board.set_value(pos, Value2D(pos, count=value))
            logger.debug(f"Set {pos} to 2D''[{value}]")
        return board
    
class Value2D(AbstractClueValue):
    def __init__(self, pos: AbstractPosition, count: int = 0, code: bytes = None):
        super().__init__(pos, code)
        if code is not None:
            # 从字节码解码
            self.count = code[0]
        else:
            # 直接初始化
            self.count = count
        self.neighbors = []
        for _pos in [pos.up(1), pos.down(1), pos.right(1), pos.left(1)]:
            self.neighbors.append(_pos.neighbors(0, 2))

    def __repr__(self):
        return f"{self.count}"
    
    @classmethod
    def type(cls) -> bytes:
        return Rule2D.name[0].encode("ascii")
    
    def code(self) -> bytes:
        return bytes([self.count])
    
    def high_light(self, board: AbstractBoard) -> List[AbstractPosition] | None:
        highlight_positions = []
        for neighbor in self.neighbors:
            highlight_positions.extend(neighbor)
        return highlight_positions
    
    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        d1 = model.NewBoolVar(f"d1_{self.pos}")
        d2 = model.NewBoolVar(f"d2_{self.pos}")
        d3 = model.NewBoolVar(f"d3_{self.pos}")
        d4 = model.NewBoolVar(f"d4_{self.pos}")
        vars_list = [d1, d2, d3, d4]

        model.Add(sum(board.batch(self.neighbors[0], mode='variable', drop_none=True)) == self.count).OnlyEnforceIf(d1, s)
        model.Add(sum(board.batch(self.neighbors[0], mode='variable', drop_none=True)) != self.count).OnlyEnforceIf(d1.Not(), s)
        model.Add(sum(board.batch(self.neighbors[1], mode='variable', drop_none=True)) <= self.count).OnlyEnforceIf(d1, s)
        model.Add(sum(board.batch(self.neighbors[2], mode='variable', drop_none=True)) <= self.count).OnlyEnforceIf(d1, s)
        model.Add(sum(board.batch(self.neighbors[3], mode='variable', drop_none=True)) <= self.count).OnlyEnforceIf(d1, s)

        model.Add(sum(board.batch(self.neighbors[1], mode='variable', drop_none=True)) == self.count).OnlyEnforceIf(d2, s)
        model.Add(sum(board.batch(self.neighbors[1], mode='variable', drop_none=True)) != self.count).OnlyEnforceIf(d2.Not(), s)
        model.Add(sum(board.batch(self.neighbors[0], mode='variable', drop_none=True)) <= self.count).OnlyEnforceIf(d2, s)
        model.Add(sum(board.batch(self.neighbors[2], mode='variable', drop_none=True)) <= self.count).OnlyEnforceIf(d2, s)
        model.Add(sum(board.batch(self.neighbors[3], mode='variable', drop_none=True)) <= self.count).OnlyEnforceIf(d2, s)

        model.Add(sum(board.batch(self.neighbors[2], mode='variable', drop_none=True)) == self.count).OnlyEnforceIf(d3, s)
        model.Add(sum(board.batch(self.neighbors[2], mode='variable', drop_none=True)) != self.count).OnlyEnforceIf(d3.Not(), s)
        model.Add(sum(board.batch(self.neighbors[0], mode='variable', drop_none=True)) <= self.count).OnlyEnforceIf(d3, s)
        model.Add(sum(board.batch(self.neighbors[1], mode='variable', drop_none=True)) <= self.count).OnlyEnforceIf(d3, s)
        model.Add(sum(board.batch(self.neighbors[3], mode='variable', drop_none=True)) <= self.count).OnlyEnforceIf(d3, s)

        model.Add(sum(board.batch(self.neighbors[3], mode='variable', drop_none=True)) == self.count).OnlyEnforceIf(d4, s)
        model.Add(sum(board.batch(self.neighbors[3], mode='variable', drop_none=True)) != self.count).OnlyEnforceIf(d4.Not(), s)
        model.Add(sum(board.batch(self.neighbors[0], mode='variable', drop_none=True)) <= self.count).OnlyEnforceIf(d4, s)
        model.Add(sum(board.batch(self.neighbors[1], mode='variable', drop_none=True)) <= self.count).OnlyEnforceIf(d4, s)
        model.Add(sum(board.batch(self.neighbors[2], mode='variable', drop_none=True)) <= self.count).OnlyEnforceIf(d4, s)

        model.AddBoolOr(vars_list).OnlyEnforceIf(s)
