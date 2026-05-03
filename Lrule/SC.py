"""
[SC] 甘蔗 (Sugar Cane)：每个雷周围四格至少有一个染色格, 且染色格不能为雷
"""

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard
from minesweepervariants.impl.summon.solver import Switch

class RuleSC(AbstractMinesRule):
    id = "SC"
    name = "Sugar Cane"
    name.zh_CN = "甘蔗"
    doc = "Each mine must have at least one dyed cell among its 4 adjacent cells, and dyed cells cannot be mines"
    doc.zh_CN = "每个雷周围至少有一个染色格, 且染色格不能为雷"
    author = ("NT", 2201963934)
    tags = ["Original", "Local", "Dyed"]

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)
        for pos, var in board(mode="var"):
            if board.get_dyed(pos):
                model.Add(var == 0).OnlyEnforceIf(s)
                continue
            var_list = board.batch(pos.neighbors(1), mode="dye", drop_none=True)
            if not any(var_list):
                model.Add(var == 0).OnlyEnforceIf(s)