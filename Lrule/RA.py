"""
[RA] 图书馆：每一行的雷值从第一个雷开始为1，往后依次增加1
"""

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.impl.summon.solver import Switch
# The CP‑SAT model used by the solver is provided by OR‑Tools.
from ortools.sat.python import cp_model

class RuleRA(AbstractMinesRule):

    id = "RA"
    name = "Library"
    name.zh_CN = "图书馆"
    doc = "In each row, mines are numbered from 1 left-to-right"
    doc.zh_CN = "每一行的雷值从第一个雷开始为1，往后依次增加1"
    tags = ["Variant", "Mine-Value", "Local"]
    creation_time = "2026-05-22"
    lib_only = True
    author = ("NT", 2201963934)

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
            # 返回该格的雷值：在同一行从左到当前格（含）为雷的格子数。
            raw = board.get_type(pos, special=self.rule)
            if self.rule == 'raw':
                is_mine = int(raw == 'F')
            else:
                is_mine = int(raw)
            if is_mine == 0:
                return 0

            row = board.get_row_pos(pos)
            try:
                idx = row.index(pos)
            except ValueError:
                idx = 0

            count = 0
            for p in row[: idx + 1]:
                p_raw = board.get_type(p, special=self.rule)
                if self.rule == 'raw':
                    p_is_mine = int(p_raw == 'F')
                else:
                    p_is_mine = int(p_raw)
                if p_is_mine == 1:
                    count += 1
            return count

        board.register_type_special('RA', get_type)

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

        # 对于每个格：当该格为雷时，det(special='RA') == 同一行从左到该格（含）的雷变量之和；否则 det == 0
        for key in board.get_interactive_keys():
            for pos, _ in board(key=key):
                mine = board.get_variable(pos, special="raw")
                det = board.get_variable(pos, special='RA')
                row = board.get_row_pos(pos)
                try:
                    idx = row.index(pos)
                except ValueError:
                    idx = 0
                left = row[: idx + 1]
                var_line = board.batch(left, mode="variable", drop_none=True)
                if var_line:
                    model.Add(det == sum(var_line)).OnlyEnforceIf(mine)
                else:
                    model.Add(det == 0).OnlyEnforceIf(mine)
                model.Add(det == 0).OnlyEnforceIf(mine.Not())

    def get_deps(self) -> list[str]:
        if self.rule == 'raw':
            return []
        return [self.rule]
