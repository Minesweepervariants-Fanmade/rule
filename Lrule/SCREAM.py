"""
[4S]阶梯: 所有雷被视为 X 个雷（X 为其的行列数之和）
"""
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.impl.summon.solver import Switch
from ortools.sat.python.cp_model import CpModel

class Rule3I(AbstractMinesRule):
    name = ["SCREAM", "尖叫"]
    doc = ""
    lib_only = True

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        self.onboard_init(board)

    def onboard_init(self, board: 'AbstractBoard'):
        board.register_type_special(self.name[0], self.get_type)

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch') -> None:
        model = board.get_model()
        sw = switch.get(model, self)
        for key in board.get_interactive_keys():
            for pos, _ in board(key=key):
                raw = board.get_variable(pos, special='raw')
                det = board.get_variable(pos, special=self.name[0])

                neighbor_vars = board.batch(pos.neighbors(1), "var", special='raw', drop_none=True)
                # If there are no neighbor variables, the sum is 0 -> treated as <=1
                if not neighbor_vars:
                    model.Add(det == 1).OnlyEnforceIf(raw)
                else:
                    neighbor_sum = sum(neighbor_vars)

                    # create BoolVars that are equivalent to the comparisons
                    b_le1 = model.NewBoolVar(f"{self.name[0]}_le1_{key}_{pos}")
                    model.Add(neighbor_sum <= 1).OnlyEnforceIf(b_le1)
                    model.Add(neighbor_sum > 1).OnlyEnforceIf(b_le1.Not())

                    b_eq2 = model.NewBoolVar(f"{self.name[0]}_eq2_{key}_{pos}")
                    model.Add(neighbor_sum == 2).OnlyEnforceIf(b_eq2)
                    model.Add(neighbor_sum != 2).OnlyEnforceIf(b_eq2.Not())

                    b_eq3 = model.NewBoolVar(f"{self.name[0]}_eq3_{key}_{pos}")
                    model.Add(neighbor_sum == 3).OnlyEnforceIf(b_eq3)
                    model.Add(neighbor_sum != 3).OnlyEnforceIf(b_eq3.Not())

                    b_ge4 = model.NewBoolVar(f"{self.name[0]}_ge4_{key}_{pos}")
                    model.Add(neighbor_sum >= 4).OnlyEnforceIf(b_ge4)
                    model.Add(neighbor_sum < 4).OnlyEnforceIf(b_ge4.Not())

                    # link det values to raw and the comparison booleans
                    model.Add(det == 1).OnlyEnforceIf([raw, b_le1])
                    model.Add(det == 2).OnlyEnforceIf([raw, b_eq2])
                    model.Add(det == 6).OnlyEnforceIf([raw, b_eq3])
                    model.Add(det == 24).OnlyEnforceIf([raw, b_ge4])
                    model.Add(det == 0).OnlyEnforceIf(raw.Not())

    @staticmethod
    def get_type(board: 'AbstractBoard', pos: 'AbstractPosition', *args, **kwargs):
        value = board.get_type(pos, special='raw')

        if value == "F":
            s = board.batch(pos.neighbors(1), "type", special='raw').count("F")
            return [1, 1, 2, 6, 24][min(s, 4)]
        else:
            return 0