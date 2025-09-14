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

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)
        for key in board.get_interactive_keys():
            for pos, _ in board(key=key):
                inverted_var = board.get_variable(pos, "3I")
                if board.get_dyed(pos):
                    model.Add(inverted_var == board.get_variable(pos).Not()).OnlyEnforceIf(s)
                else:
                    model.Add(inverted_var == board.get_variable(pos)).OnlyEnforceIf(s)
