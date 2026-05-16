"""
[First] 每行的左数第一个雷视为两个雷
"""

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.impl.summon.solver import Switch

class RuleFirst(AbstractMinesRule):
    id = "First"
    name = "First"
    name.zh_CN = "首雷双值"
    doc = "The leftmost mine in each row counts as two mines"
    doc.zh_CN = "每行的左数第一个雷视为两个雷"
    tags = ["Variant", "Mine-Value", "Local"]
    creation_time = "2026-05-17"
    lib_only = True
    author = ("Artless", 2452944138)

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        self.onboard_init(board)
        self.rule = data or "raw"

    def onboard_init(self, board: 'AbstractBoard'):
        def get_type(board: 'AbstractBoard', pos: 'AbstractPosition', *args, **kwargs):
            """Return the effective mine value for *pos* based only on board state.

            The rule: *the left‑most mine in each row counts as two*.  This
            function must not depend on CP‑SAT variables because it can be
            invoked before the model is solved (e.g., during clue generation).
            We therefore examine the raw type information of the current cell
            and of all cells to its left in the same row.
            """

            # ----- Determine whether this cell is a mine -----
            raw = board.get_type(pos, special=self.rule)
            if self.rule == 'raw':
                is_mine = int(raw == 'F')
            else:
                is_mine = int(raw)
            if is_mine == 0:
                return 0

            # ----- Look for any mine to the left in the same row -----
            # ``board.get_row_pos`` returns all positions in the same row (same x).
            # We consider only positions with a smaller y (i.e., to the left).
            for left in board.get_row_pos(pos):
                if left.y >= pos.y:
                    # Positions to the right (or the same) are not "left".
                    continue
                left_raw = board.get_type(left, special=self.rule)
                if self.rule == 'raw':
                    left_is_mine = int(left_raw == 'F')
                else:
                    left_is_mine = int(left_raw)
                if left_is_mine == 1:
                    # There is a mine to the left → not the left‑most.
                    return 1
            # No mine to the left → this is the left‑most mine.
            return 2
        board.register_type_special('First', get_type)

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch') -> None:

        model = board.get_model()
        s = switch.get(model, self)
        # Collect left‑most flags per row (row identified by x coordinate).
        row_flags: dict[int, list['ortools.sat.python.cp_model.BoolVar']] = {}
        for key in board.get_interactive_keys():
            for pos, _ in board(key=key):
                mine = board.get_variable(pos, special="raw")
                det = board.get_variable(pos, special='First')
                is_leftmost = model.NewBoolVar(
                    f"leftmost_{key}_{pos.x}_{pos.y}")
                # Store flag for later uniqueness check.
                row_flags.setdefault(pos.x, []).append(is_leftmost)

                # Flag can be true only if this cell is a mine.
                model.Add(is_leftmost <= mine)

                # No earlier mine may exist in the same row (smaller y).
                for other in board.get_row_pos(pos):
                    if other.y >= pos.y:
                        continue
                    other_mine = board.get_variable(other, special="raw")
                    model.Add(is_leftmost + other_mine <= 1)

                # Effective value definition.
                model.Add(det == mine + is_leftmost)

        # Enforce at most one left‑most mine per row.
        for flags in row_flags.values():
            model.Add(sum(flags) <= 1).OnlyEnforceIf(s)

    def get_deps(self) -> list[str]:
        if self.rule == 'raw':
            return []
        return [self.rule]
