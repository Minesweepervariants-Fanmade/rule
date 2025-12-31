from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard

from .connect import connect

class Rule1S(AbstractMinesRule):
    name = ["4D", "对角"]
    doc = "不同四连通雷区不可对角相邻"

    def create_constraints(self, board: AbstractBoard, switch):
        model = board.get_model()
        s = switch.get(model, self)

        positions_vars = [(pos, var) for pos, var in board("always", mode="variable")]
        n = len(positions_vars)
        four_connect_groups = model.NewIntVar(1, n, "four_connect_groups")
        eight_connect_groups = model.NewIntVar(1, n, "eight_connect_groups")

        connect(
            model=model,
            board=board,
            connect_value=1,
            nei_value=1,
            switch=s,
            component_num=four_connect_groups
        )

        connect(
            model=model,
            board=board,
            connect_value=1,
            nei_value=2,
            switch=s,
            component_num=eight_connect_groups
        )

        model.Add(four_connect_groups == eight_connect_groups).OnlyEnforceIf(s)
