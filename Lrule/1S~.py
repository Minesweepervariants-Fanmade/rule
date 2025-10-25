from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard

from .connect import connect

class Rule1S(AbstractMinesRule):
    name = ["1S~", "S~", "蛇~", "Snake~"]
    doc = "所有非雷构成若干条蛇。蛇是一条宽度为 1 的四连通路径，不存在分叉、环、交叉。"

    def create_constraints(self, board: AbstractBoard, switch):
        model = board.get_model()
        s = switch.get(model, self)
        
        root_vars = []
        one_connect_vars = []

        for pos, obj in board(mode="object"):
            root_vars.append(model.NewBoolVar(f"root_{pos}"))
            one_connect_vars.append(model.NewBoolVar(f"one_connect_{pos}"))

        connect(
            model=model,
            board=board,
            connect_value=0,
            nei_value=1,
            switch=s,
            root_vars=root_vars
        )

        for i, (pos, var) in enumerate(board(mode="variable")):
            var_list = [var.Not() for var in board.batch(pos.neighbors(1), mode="variable", drop_none=True)]
            model.Add(sum(var_list) < 3).OnlyEnforceIf([var.Not(), s])
            model.Add(sum(var_list) > 0).OnlyEnforceIf([var.Not(), s])
            model.Add(sum(var_list) == 1).OnlyEnforceIf([one_connect_vars[i], s])
            model.Add(var == 0).OnlyEnforceIf([one_connect_vars[i], s])

        model.Add(sum(one_connect_vars) == 2 * sum(root_vars)).OnlyEnforceIf(s)
