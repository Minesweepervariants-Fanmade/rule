"""
[1HT] 纵向 (Vertical)：所有雷不能与其他雷纵向相邻
"""
from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class Rule1HT(AbstractMinesRule):
    name = ["1HT", "HT", "纵向", "Vertical"]
    doc = "所有雷不能与其他雷纵向相邻"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        for pos, var in board(mode="variable"):
            if board.in_bounds(pos.up()):
                model.Add(board.get_variable(pos.up()) == 0).OnlyEnforceIf([var, s])
            if board.in_bounds(pos.down()):
                model.Add(board.get_variable(pos.down()) == 0).OnlyEnforceIf([var, s])

    def suggest_total(self, info: dict):
        ub = 0
        for key in info["interactive"]:
            total = info["total"][key]
            ub += total
        def a(model, total):
            s = model.NewIntVar(0, 2, "s")
            model.AddModuloEquality(s, total, 2)
            model.AddHint(s, 0)
            model.Add(s != 1)
        info["soft_fn"](ub * 0.295, 0)
        info["hard_fns"].append(a)
