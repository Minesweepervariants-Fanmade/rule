from minesweepervariants.abs.Lrule import AbstractMinesRule

NAME_2I = "2I1C"

class Rule2I1C(AbstractMinesRule):
    def __init__(self, board = None, data=None):
        super().__init__(board, data)
        board.generate_board(NAME_2I, (3, 3))

    def create_constraints(self, board, switch):
        ...


