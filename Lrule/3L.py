"""
[3L] 环：所有雷构成一条环。环是一条宽度为 1 的八连通路径，不存在分叉和交叉, 环的头尾相连
"""
from ....abs.Lrule import AbstractMinesRule

from .connect import connect


class Rule1S(AbstractMinesRule):
    name = ["3L", "环", "Loop"]
    doc = "所有雷构成一条环。环是一条宽度为 1 的八连通路径，不存在分叉和交叉，环的头尾相连"

    def create_constraints(self, board, switch):
        model = board.get_model()
        s = switch.get(model, self)

        connect(
            model=model,
            board=board,
            connect_value=1,
            nei_value=2,
            switch=s,
        )

        for pos, var in board(mode="variable"):
            var_list = board.batch(pos.neighbors(2), mode="variable", drop_none=True)
            model.Add(sum(var_list) == 2).OnlyEnforceIf([var, s])
