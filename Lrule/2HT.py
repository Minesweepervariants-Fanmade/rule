"""
[2HT] 纵向 (Vertical)：所有雷必须存在纵向相邻的雷
"""
from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class Rule2HT(AbstractMinesRule):
    name = ["2HT", "纵向", "Vertical"]
    doc = "所有雷必须存在纵向相邻的雷"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        for pos, var in board(mode="variable"):
            if not board.in_bounds(pos.down()):
                model.Add(board.get_variable(pos.up()) == 1).OnlyEnforceIf([var, s])
            elif not board.in_bounds(pos.up()):
                model.Add(board.get_variable(pos.down()) == 1).OnlyEnforceIf([var, s])
            else:
                model.AddBoolOr(board.batch([pos.down(), pos.up()], mode="variable")).OnlyEnforceIf([var, s])
