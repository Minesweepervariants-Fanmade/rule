"""
[5N] 相邻: 每个雷的相邻四格至少存在一个雷
"""

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.impl.summon.solver import Switch


class Rule5N(AbstractMinesRule):
    id = "5N"
    name = "Adjacent"
    name.zh_CN = "相邻"
    doc = "Each mine has at least one mine in the four orthogonal adjacent cells"
    doc.zh_CN = "每个雷的相邻四格至少存在一个雷"
    tags = ["Creative", "Local", "Connectivity"]
    creation_time = "2026-09-13"
    author = ("\u96fe", 3140864122)

    def create_constraints(self, board: 'Board', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)
        for pos, var in board(mode="var"):
            var_list = board.batch(pos.neighbors(1), mode="var", drop_none=True)
            model.Add(sum(var_list) >= 1).OnlyEnforceIf([var, s])

    def suggest_total(self, info: dict):
        ub = 0
        for key in info["interactive"]:
            total = info["total"][key]
            ub += total

        info["soft_fn"](ub * 0.5, 0)
