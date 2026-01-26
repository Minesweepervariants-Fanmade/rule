from typing import List

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.impl.summon.solver import Switch

class Rule3Q(AbstractMinesRule):
    name = ["3Q'", "无方"]
    doc = "任意四个雷不能作为一个横平竖直的矩形的顶点"

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)

        for pos, _ in board(mode="var"):
            right_bound = pos
            while board.is_valid(right_bound.right()):
                down_bound = pos
                right_bound = right_bound.right()
                while board.is_valid(down_bound.down()):
                    down_bound = down_bound.down()
                    block_pos = [
                        pos,
                        right_bound,
                        down_bound,
                        board.get_pos(down_bound.x, right_bound.y, pos.board_key)
                    ]
                    block_var = board.batch(block_pos, mode="var")
                    model.Add(sum(block_var) != 4).OnlyEnforceIf(s)

    def suggest_total(self, info: dict):
        def a(model, total):
            model.AddModuloEquality(0, total, 2)

        ub = 0
        for key in info["interactive"]:
            total = info["total"][key]
            ub += total

        info["soft_fn"](ub * 0.295, 0)
        info["hard_fns"].append(a)
