"""
[4S'']阶梯'': 4S'' = 4S - 1 = 4S' + 1
"""
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.solver import Switch
from ortools.sat.python.cp_model import CpModel

class Rule3I(AbstractMinesRule):
    id = "4S''"
    name = "Staircase''"
    name.zh_CN = "阶梯''"
    doc = "4S'' = 4S - 1 = 4S' + 1"
    author = ("NT", 2201963934)
    lib_only = True

    tags = ["Variant", "Global", "Mine-Value"]
    creation_time = "2025-10-26"

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        self.onboard_init(board)

    def onboard_init(self, board: 'Board'):
        board.register_type_special('4S\'\'', self.get_type)


    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)
        for key in board.get_interactive_keys():
            for pos, _ in board(key=key):
                raw = board.get_variable(pos, special='raw')
                det = board.get_variable(pos, special='4S\'\'')
                model.Add(det == pos.x + pos.y + 1).OnlyEnforceIf(raw)
                model.Add(det == 0).OnlyEnforceIf(raw.Not())

    @staticmethod
    def get_type(board: 'Board', pos: 'Position', *args, **kwargs):
        value = board.get_type(pos, special='raw')

        if value == "F":
            return pos.x + pos.y + 1
        else:
            return 0