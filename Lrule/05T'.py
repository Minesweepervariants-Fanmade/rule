"""
[0.5T'] 无三角：盘面上所有雷共线。
"""

from itertools import combinations

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.position import Position


class Rule05Tp(AbstractMinesRule):
    id = "0.5T'"
    name = "No Triangle"
    name.zh_CN = "无三角"
    doc = "All mines on the board are collinear."
    doc.zh_CN = "盘面上所有雷共线"
    author = ("NT", 2201963934)
    tags = ["Variant", "Anti-Construction", "Global"]
    creation_time = "2026-11-26"

    @staticmethod
    def _are_collinear(p1: Position, p2: Position, p3: Position) -> bool:
        """Return whether the three cell centres lie on one straight line."""
        return (
            (p2.col - p1.col) * (p3.row - p1.row)
            == (p2.row - p1.row) * (p3.col - p1.col)
        )

    def create_constraints(self, board: Board, switch) -> None:
        model = board.get_model()
        rule_switch = switch.get(model, self)

        for key in board.get_interactive_keys():
            positions = list(board(key=key, mode="variable"))

            # A mine set is collinear exactly when it contains no
            # non-collinear triple. Sets with fewer than three mines satisfy
            # the rule vacuously.
            for triple in combinations(positions, 3):
                if self._are_collinear(*(pos for pos, _ in triple)):
                    continue

                model.add_bool_or([var.Not() for _, var in triple]).only_enforce_if(
                    rule_switch
                )

    def suggest_total(self, info: dict) -> None:
        # A line in a rectangular grid contains at most max(width, height)
        # cells. Aim slightly below that limit so generation has a wider
        # choice of slopes than only full rows, columns, and main diagonals.
        target = 0.0
        for key in info["interactive"]:
            width, height = info["size"][key]
            target += max(width, height) * 0.8
        info["soft_fn"](target, 0)
