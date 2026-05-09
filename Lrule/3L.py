"""
[3L] 环：所有雷构成一条环。环是一条宽度为 1 的八连通路径，不存在分叉和交叉, 环的头尾相连
"""
from ....abs.Lrule import AbstractMinesRule

from .connect import connect


class Rule1S(AbstractMinesRule):
    id = "3L"
    name = "Loop"
    name.zh_CN = "环"
    doc = "All mines form a loop. A loop is a width-1 diagonal path without branches or intersections, and the loop connects head to tail"
    doc.zh_CN = "所有雷构成一条环。环是一条宽度为 1 的八连通路径，不存在分叉和交叉，环的头尾相连"
    tags = ["Creative", "Connectivity", "Construction", "Global"]
    creation_time = "2025-08-22"
    author = ("", 0)

    def create_constraints(self, board, switch):
        model = board.get_model()
        s = switch.get(model, self)

        positions = [(k, p, v) for k in board.get_interactive_keys() for p, v in board(key=k, mode="variable")]
        n = len(positions)
        if n < 2:
            return

        # 边变量：八连通且两端都是雷格
        arcs, arc_var = [], {}
        for i, (k1, p1, mv1) in enumerate(positions):
            for j, (k2, p2, mv2) in enumerate(positions):
                if i != j and p2 in p1.neighbors(2):
                    v = model.new_bool_var(f'5L_{i}_{j}')
                    arc_var[i, j] = v
                    arcs.append((i, j, v))
                    model.add(v == 0).OnlyEnforceIf(mv1.Not())
                    model.add(v == 0).OnlyEnforceIf(mv2.Not())

        # 自环跳过非雷格节点
        for i, (_, _, mv) in enumerate(positions):
            arcs.append((i, i, mv.Not()))

        model.add_circuit(arcs).OnlyEnforceIf(s)

        for pos, var in board(mode="variable"):
            var_list = board.batch(pos.neighbors(2), mode="variable", drop_none=True)
            model.add(sum(var_list) == 2).OnlyEnforceIf([var, s])
