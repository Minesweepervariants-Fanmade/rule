"""
[1N] 负雷 (Negative)：线索表示 3x3 范围内染色格与非染色格的雷数差
"""
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.impl.summon.solver import Switch
from ortools.sat.python.cp_model import CpModel

class Rule1N(AbstractMinesRule):
    name = ["1N", "N", "负雷", "Negative"]
    doc = "染色格中雷值取负"

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        self.onboard_init(board)
        self.rule = data or "raw"

    def onboard_init(self, board: 'AbstractBoard'):
        def get_type(board: 'AbstractBoard', pos: 'AbstractPosition', *args, **kwargs):
            value = board.get_type(pos, special=self.rule)

            if self.rule == 'raw':
                value = value == 'F'
            else:
                value = int(value)

            if board.get_dyed(pos):
                return -value
            else:
                return value

        board.register_type_special('1N', get_type)


    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)
        for key in board.get_interactive_keys():
            for pos, _ in board(key=key):
                mine = board.get_variable(pos, special="raw")
                raw = board.get_variable(pos, special=self.rule)
                det = board.get_variable(pos, special='1N')
                if board.get_dyed(pos):
                    model.Add(det == -raw).OnlyEnforceIf(mine)
                model.Add(det == 0).OnlyEnforceIf(mine.Not())