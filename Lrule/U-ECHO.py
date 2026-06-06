"""
[U-ECHO]回声：抛出参数。
"""

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board


class UEchoError(Exception):
    pass


class RuleUECHO(AbstractMinesRule):
    id = "U-ECHO"
    name = "echo"
    name.zh_CN = "回声"
    doc = "Echo: outputs the parameter"
    doc.zh_CN = "回声：抛出参数。"
    author = ("NT", 2201963934)
    tags = ["Creative", "Parameter", "WIP"]
    creation_time = "2026-04-11"

    def __init__(self, board: Board, data=None):
        super().__init__(board, data)
        raise UEchoError(data)

    def create_constraints(self, board: 'Board', switch):
        return
