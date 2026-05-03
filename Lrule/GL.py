"""
[GL] 生命游戏 (Game of Life)：每个雷周围八格中恰有2或3个雷。
"""

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard
from minesweepervariants.impl.summon.solver import Switch

class RuleGL(AbstractMinesRule):
    id = "GL"
    name = "Game of Life"
    name.zh_CN = "生命游戏"
    doc = "Each mine has exactly 2 or 3 mines in the eight surrounding cells"
    doc.zh_CN = "每个雷周围八格中恰有2或3个雷"
    tags = ["Creative", "Local", "Strong"]

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)
        for pos, var in board(mode="var"):
            var_list = board.batch(pos.neighbors(2), mode="var", drop_none=True)
            model.Add(sum(var_list) >= 2).OnlyEnforceIf([var, s])
            model.Add(sum(var_list) <= 3).OnlyEnforceIf([var, s])
