from ....abs.Lrule import AbstractMinesRule

class RuleA2(AbstractMinesRule):
    name = ["A2", "A2"]
    doc = "A2 格是雷"

    def create_constraints(self, board, switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            model.Add(board.get_variable(board.get_pos(1, 2, key)) == 1).OnlyEnforceIf(s)
