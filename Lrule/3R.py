"""
[3R]引用：在第 X 行或第 X 列的格子的周围八格不能恰好有 X 个雷
"""

from ....abs.board import AbstractBoard
from ....abs.Lrule import AbstractMinesRule


class Rule1T(AbstractMinesRule):
    name = ["3R", "引用", "Reference"]
    doc = "在第 X 行或第 X 列的格子的周围八格不能恰好有 X 个雷"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        for pos, _ in board():
            var_list = board.batch(pos.neighbors(2), mode="variable", drop_none=True)
            model.Add(sum(var_list) != pos.x + 1).OnlyEnforceIf(s)
            model.Add(sum(var_list) != pos.y + 1).OnlyEnforceIf(s)
