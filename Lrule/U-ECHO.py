"""
[U-ECHO]回声：抛出参数。
"""

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class UEchoError(Exception):
    pass


class RuleUECHO(AbstractMinesRule):
    id = "U-ECHO"
    name = "echo"
    name.zh_CN = "回声"
    doc = "回声：抛出参数。"
    author = ("NT", 2201963934)

    def __init__(self, board: AbstractBoard, data=None):
        super().__init__(board, data)
        raise UEchoError(data)

    def create_constraints(self, board: 'AbstractBoard', switch):
        return
