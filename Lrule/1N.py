"""
[1N] 负雷 (Negative)：线索表示 3x3 范围内染色格与非染色格的雷数差
"""
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.solver import Switch
from ortools.sat.python.cp_model import CpModel

class Rule1N(AbstractMinesRule):
    id = "1N"
    aliases = ("N",)
    name = "Negative"
    name.zh_CN = "负雷"
    doc = "Mine value becomes negative in dyed cells"
    doc.zh_CN = "染色格中雷值取负"
    tags = ["Variant", "Dyed", "Mine-Value", "Local"]
    creation_time = "2025-10-26"
    lib_only = True
    author = ("", 0)

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        self.onboard_init(board)
        self.rule = data or "raw"

    def onboard_init(self, board: 'Board'):
        def get_type(board: 'Board', pos: 'Position', *args, **kwargs):
            value = board.get_type(pos, special=self.rule)

            if self.rule == 'raw':
                value = value == 'F'
            else:
                value = int(value)

            if board.get_dyed(pos):
                return -value
            else:
                return value

        board.register_type_special('1N', get_type)


    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)
        for key in board.get_interactive_keys():
            for pos, _ in board(key=key):
                mine = board.get_variable(pos, special="raw")
                raw = board.get_variable(pos, special=self.rule)
                det = board.get_variable(pos, special='1N')
                if board.get_dyed(pos):
                    model.Add(det == -raw).OnlyEnforceIf(mine)
                else:
                    model.Add(det == raw).OnlyEnforceIf(mine)
                model.Add(det == 0).OnlyEnforceIf(mine.Not())

    def get_deps(self) -> list[str]:
        if self.rule == 'raw':
            return []
        else:
            return [self.rule]

    def companion_id(self) -> str:
        return "V''"
