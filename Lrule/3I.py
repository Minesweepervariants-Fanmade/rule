"""
[3I]反相(Inverted): 染色格中非雷视为雷，雷视为非雷
"""
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.impl.summon.solver import Switch
from ortools.sat.python.cp_model import CpModel

class Rule3I(AbstractMinesRule):
    name = ["3I", "反相"]
    doc = "染色格中非雷视为雷，雷视为非雷"

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        self.enforce = False
        if data == '!':
            self.enforce = True
        self.onboard_init(board)

    def onboard_init(self, board: 'AbstractBoard'):
        board.register_type_special('3I', self.get_type)

        if self.enforce and board.default_special != "3I":
            board.set_default_special('3I')


    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)
        for key in board.get_interactive_keys():
            for pos, _ in board(key=key):
                inverted_var = board.get_variable(pos, special="3I")
                if board.get_dyed(pos):
                    model.Add(inverted_var == board.get_variable(pos, special='raw').Not()).OnlyEnforceIf(s)
                else:
                    model.Add(inverted_var == board.get_variable(pos, special='raw')).OnlyEnforceIf(s)

    @staticmethod
    def get_type(board: 'AbstractBoard', pos: 'AbstractPosition', *args, **kwargs) -> str:
        value = board.get_type(pos, special='raw')
        if board.get_dyed(pos):
            if value == "C":
                return "F"
            elif value == "F":
                return "N"
            elif value == "N":
                return "F"
        return value