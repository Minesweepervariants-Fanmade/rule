"""
[4S]阶梯: 所有雷被视为 X 个雷（X 为其的行列数之和）
"""
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.impl.summon.solver import Switch
from ortools.sat.python.cp_model import CpModel

class Rule3I(AbstractMinesRule):
    name = ["4S", "阶梯", "Staircase"]
    doc = "所有雷被视为 X 个雷（X 为其的行列数之和）"
    lib_only = True

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        self.onboard_init(board)

    def onboard_init(self, board: 'AbstractBoard'):
        board.register_type_special('4S', self.get_type)

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)
        for key in board.get_interactive_keys():
            for pos, _ in board(key=key):
                raw = board.get_variable(pos, special='raw')
                det = board.get_variable(pos, special='4S')
                model.Add(det == pos.x + pos.y + 2).OnlyEnforceIf(raw)
                model.Add(det == 0).OnlyEnforceIf(raw.Not())

    @staticmethod
    def get_type(board: 'AbstractBoard', pos: 'AbstractPosition', *args, **kwargs):
        value = board.get_type(pos, special='raw')

        if value == "F":
            return pos.x + pos.y + 2
        else:
            return 0