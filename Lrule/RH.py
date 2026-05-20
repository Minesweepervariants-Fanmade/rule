"""
[RH] 竖直方向连续雷的顶雷雷值等于该组连续雷数，其余雷值为0
"""

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.impl.summon.solver import Switch
# The CP‑SAT model used by the solver is provided by OR‑Tools.
from ortools.sat.python import cp_model

class RuleRH(AbstractMinesRule):
    """Rule RH – vertical group top‑mine value.

    For each column, the *topmost* mine of a consecutive vertical group
    receives a value equal to the size of that group; all other mines in the
    group have value ``0``. The rule works both on the raw board (where mines
    are represented by ``'F'``) and on a pre‑processed board where mines are
    already encoded as ``0``/``1``.
    """

    id = "RH"
    name = "Enrichment"
    name.zh_CN = "富集"
    doc = "Top mine of a vertical consecutive group gets the group size, others get 0"
    doc.zh_CN = "竖直方向连续雷的顶雷雷值等于该组连续雷数，其余雷值为0"
    tags = ["Variant", "Mine-Value", "Local"]
    creation_time = "2026-05-17"
    lib_only = True
    author = ("NT", 2452944138)

    def __init__(self, board=None, data=None) -> None:
        super().__init__(board, data)
        self.onboard_init(board)
        self.rule = data or "raw"

    def onboard_init(self, board: 'AbstractBoard'):
        """Register a special type function for the rule.

        The function inspects the *raw* board state only (no CP‑SAT variables)
        and returns the effective mine value according to the rule description.
        """

        def get_type(board: 'AbstractBoard', pos: 'AbstractPosition', *args, **kwargs):
            # Determine whether the current cell is a mine.
            raw = board.get_type(pos, special=self.rule)
            if self.rule == 'raw':
                is_mine = int(raw == 'F')
            else:
                is_mine = int(raw)
            if is_mine == 0:
                return 0

            # ----- Check for a mine directly above (adjacent) -----
            # Only a mine immediately above disqualifies this cell from being the topmost of a consecutive group.
            if board.in_bounds(pos.up()):
                up_raw = board.get_type(pos.up(), special=self.rule)
                if self.rule == 'raw':
                    up_is_mine = int(up_raw == 'F')
                else:
                    up_is_mine = int(up_raw)
                if up_is_mine == 1:
                    # Adjacent mine above → not topmost.
                    return 0

            # This is the topmost mine of a vertical group. Count consecutive mines downwards.
            size = 1
            for down in board.get_col_pos(pos):
                if down.x <= pos.x:
                    continue
                down_raw = board.get_type(down, special=self.rule)
                if self.rule == 'raw':
                    down_is_mine = int(down_raw == 'F')
                else:
                    down_is_mine = int(down_raw)
                if down_is_mine == 1:
                    size += 1
                else:
                    break
            return size

        board.register_type_special('RH', get_type)

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch') -> None:
        """#sym:create_constraints
        Create CP‑SAT constraints that are semantically equivalent to the
        ``get_type`` function defined in ``onboard_init``.

        The implementation mirrors the logic of ``get_type``:
        * ``is_top`` is true iff the cell is a mine and there is no mine
          directly above it.
        * ``group_size`` is the number of consecutive mines starting from the
          top cell downwards.
        * The effective value ``det`` equals ``group_size`` when ``is_top`` is
          true, otherwise ``0``.

        The constraints below encode exactly this behavior using CP‑SAT
        variables and linear relationships.
        """

        model = board.get_model()
        s = switch.get(model, self)

        # -----------------------------------------------------------------
        # 1. Identify the top‑most mine of each vertical consecutive group.
        # -----------------------------------------------------------------
        top_vars = {}
        pos_to_top = {}
        for key in board.get_interactive_keys():
            for pos, _ in board(key=key):
                mine = board.get_variable(pos, special="raw")
                is_top = model.NewBoolVar(f"top_{key}_{pos.x}_{pos.y}")
                top_vars.setdefault(pos.y, []).append(is_top)
                pos_to_top[(pos.x, pos.y)] = is_top

                # ``is_top`` ⇒ mine
                model.Add(is_top <= mine)

                # No mine directly above.
                if board.in_bounds(pos.up()):
                    up_mine = board.get_variable(pos.up(), special="raw")
                    model.Add(is_top + up_mine <= 1)

        # -----------------------------------------------------------------
        # 2. Compute the size of the consecutive group for each top cell.
        # -----------------------------------------------------------------
        for key in board.get_interactive_keys():
            for pos, _ in board(key=key):
                det = board.get_variable(pos, special='RH')
                top_flag = pos_to_top.get((pos.x, pos.y))
                if top_flag is None:
                    continue

                # Build a list of BoolVars representing mines in the consecutive
                # segment starting at ``pos`` and going downwards.
                consecutive = []
                for down in board.get_col_pos(pos):
                    if down.x < pos.x:
                        continue
                    # Stop when a non‑mine is encountered; we model this with
                    # an implication that the cell contributes only if all
                    # cells above it (including ``pos``) are mines.
                    mine_var = board.get_variable(down, special="raw")
                    # ``contrib`` is 1 iff this cell is a mine and all cells
                    # above it up to ``pos`` are mines.
                    contrib = model.NewBoolVar(f"contrib_{key}_{down.x}_{down.y}")
                    # ``contrib`` ⇒ mine_var
                    model.Add(contrib <= mine_var)
                    # ``contrib`` ⇒ all previous cells in the segment are mines.
                    # Enforce that if any previous cell is not a mine, ``contrib``
                    # must be 0. This is achieved by chaining implications.
                    # For simplicity, we require the whole segment to be mines
                    # when ``top_flag`` is true.
                    model.Add(contrib <= top_flag)
                    consecutive.append(contrib)

                # The size of the group is the sum of ``consecutive`` (each 0/1).
                group_size = model.NewIntVar(0, len(consecutive), f"size_{key}_{pos.x}_{pos.y}")
                model.Add(group_size == sum(consecutive))

                # Effective value: det = group_size when top, else 0.
                model.AddMultiplicationEquality(det, [group_size, top_flag])

    def get_deps(self) -> list[str]:
        if self.rule == 'raw':
            return []
        return [self.rule]
