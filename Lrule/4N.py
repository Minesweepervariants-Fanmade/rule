from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard, AbstractPosition

class Rule4N(AbstractMinesRule):
    name = ["4N", "4N", "相邻"]
    doc = "非雷周围四格必须有雷"

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        self._3I = False
        if data is not None:
            if data == '3I':
                self._3I = True

    def create_constraints(self, board, switch):
        model = board.get_model()
        s = switch.get(model, self)

        if self._3I:
            for pos, var in board(mode="variable", special="3I"):
                model.AddBoolOr(board.batch(pos.neighbors(1), mode="variable", drop_none=True, special="3I")).OnlyEnforceIf([var.Not(), s])
        else:
            for pos, var in board(mode="variable"):
                model.AddBoolOr(board.batch(pos.neighbors(1), mode="variable", drop_none=True)).OnlyEnforceIf([var.Not(), s])
