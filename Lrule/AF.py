"""
[AF]下落: 雷区与题板下边缘四连通
"""
from ....abs.Lrule import AbstractMinesRule
from .connect import connect_legacy as connect

class RuleAF(AbstractMinesRule):
    name = ["AF", "AF", "下落"]
    doc = "雷区与题板下边缘四连通"

    def create_constraints(self, board, switch):
        model = board.get_model()
        s = switch.get(model, self)

        positions_vars = [(pos, var) for pos, var in board("always", mode="variable")]
        root_list = [model.NewBoolVar(f'root_{i}') for i in range(len(positions_vars))]

        for index, (pos, var) in enumerate(positions_vars):
            model.Add(var == 1).OnlyEnforceIf(root_list[index])
            if pos.x != board.boundary(pos.board_key).x:
                model.Add(root_list[index] == 0)
                continue
            model.Add(root_list[index] == 1).OnlyEnforceIf(var)
            model.Add(root_list[index] == 0).OnlyEnforceIf(var.Not())

        connect(
            model,
            board,
            connect_value=1,
            nei_value=1,
            root_vars=root_list,
            ub=len(positions_vars),
            switch=s,
        )
            