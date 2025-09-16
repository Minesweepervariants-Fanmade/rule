import re

from ....abs.board import AbstractBoard
from ....abs.Lrule import AbstractMinesRule


def parse(s: str) -> list[tuple[int, int]]:
    result = []
    for part in s.split(";"):
        match = re.match(r'^([A-Z]+)(\d+)$', part)
        if match is None: raise ValueError(f"Invalid format: {part}")
        letters, number = match.groups()
        x = sum((ord(c) - ord('A') + 1) * (26 ** i) for i, c in enumerate(reversed(letters))) - 1
        y = int(number) - 1
        result.append((y, x))
    return result

class RuleA2(AbstractMinesRule):
    name = ["A2~", "A2~", "A2 格非雷"]
    doc = "A2 格非雷"

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        self.values = []
        if data is None:
            self.values = [(1, 0)]
            return

        self.values = parse(data)
        print(self.values)

    def create_constraints(self, board, switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            for pos in self.values:
                model.Add(board.get_variable(board.get_pos(*pos, key)) == 0).OnlyEnforceIf(s)
