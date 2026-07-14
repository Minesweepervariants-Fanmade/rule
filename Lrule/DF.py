"""
[DF] 异雷(Different Mine): 每个非雷格周围八格雷排布互不相同。
"""
from typing import Optional
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.position import Position


class DF(AbstractMinesRule):
    """
    Different Mine: For every two non-mine cells, the pattern of mines in their
    8-neighborhood must be distinct.
    """
    id = "DF"
    name = "Different Mine"
    name.zh_CN = "异雷"
    doc = "The mine arrangement in the 8 surrounding cells of each non-mine cell must be unique."
    doc.zh_CN = "每个非雷格周围八格雷排布互不相同。"
    author = ("NT (2201963934)", 2201963934)
    tags = ["Global", "Mine-Position"]
    creation_time = "2026-05-02"

    def create_constraints(self, board: Board, switch):
        """
        Add constraints: for any two non-mine cells, their 8-neighbour mine patterns differ.
        """
        model = board.get_model()
        if model is None:
            return

        rule_switch = switch.get(model, self)

        # Collect all valid positions
        positions = [pos for pos, _ in board(mode="variable") if board.is_valid(pos)]
        if len(positions) < 2:
            return

        # Define 8-neighbour offsets (col, row)
        offsets = [(-1, -1), (0, -1), (1, -1),
                   (-1, 0),           (1, 0),
                   (-1, 1),  (0, 1),  (1, 1)]

        # Create a pattern integer variable for each position
        pattern_vars = {}
        for pos in positions:
            pattern_var = model.NewIntVar(0, 255, f"pattern_{pos}")
            terms = []
            for bit, (dc, dr) in enumerate(offsets):
                neighbor = Position(pos.col + dc, pos.row + dr, pos.board_key)
                if board.is_valid(neighbor):
                    n_var = board.get_variable(neighbor)
                    if n_var is not None:
                        terms.append(n_var * (1 << bit))
            if terms:
                model.Add(sum(terms) == pattern_var)
            else:
                model.Add(pattern_var == 0)
            pattern_vars[pos] = pattern_var

        # For each pair of positions, enforce that if both are non-mines,
        # their patterns must differ.
        pos_list = list(positions)
        n = len(pos_list)
        for i in range(n):
            for j in range(i + 1, n):
                pos_i = pos_list[i]
                pos_j = pos_list[j]
                mine_i = board.get_variable(pos_i)
                mine_j = board.get_variable(pos_j)

                # both_non_mine == (mine_i == 0 and mine_j == 0)
                both = model.NewBoolVar(f"both_non_mine_{pos_i}_{pos_j}")
                model.Add(both <= 1 - mine_i)
                model.Add(both <= 1 - mine_j)
                model.Add(both >= (1 - mine_i) + (1 - mine_j) - 1)

                # direction variable b chooses which inequality to enforce
                b = model.NewBoolVar(f"b_{pos_i}_{pos_j}")

                # If both are non-mines, require pattern_i != pattern_j
                model.Add(pattern_vars[pos_i] - pattern_vars[pos_j] >= 1).OnlyEnforceIf([rule_switch, both, b])
                model.Add(pattern_vars[pos_i] - pattern_vars[pos_j] <= -1).OnlyEnforceIf([rule_switch, both, b.Not()])

    def suggest_total(self, info: dict):
        """
        This rule does not suggest a total mine count.
        """
        pass

    def init_board(self, board: Board) -> bool:
        """
        No special initialisation needed.
        """
        return True

    def init_clear(self, board: Board) -> None:
        """
        No special clearing needed.
        """
        pass

    def combine(self, other) -> Optional['DF']:
        """
        No combination optimization.
        """
        return None

    def get_deps(self) -> list[str]:
        """
        No dependencies.
        """
        return []
