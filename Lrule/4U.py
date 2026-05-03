from ....abs.Lrule import AbstractMinesRule

class Rule4U(AbstractMinesRule):
    id = "4U"
    name = "Cell"
    name.zh_CN = "晶胞"
    doc = "Mine distribution in the first row equals the last row, and mine distribution in the first column equals the last column"
    doc.zh_CN = "第一行和最后一行雷分布相同，第一列和最后一列雷分布相同"
    tags = ["Variant", "Global", "Anti-Construction"]

    def create_constraints(self, board, switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            x = board.boundary(key).x + 1
            y = board.boundary(key).y + 1
            for i in range(x):
                model.Add(board.get_variable(board.get_pos(i, 0, key)) == board.get_variable(board.get_pos(i, y - 1, key))).OnlyEnforceIf(s)
            for j in range(y):
                model.Add(board.get_variable(board.get_pos(0, j, key)) == board.get_variable(board.get_pos(x - 1, j, key))).OnlyEnforceIf(s)
