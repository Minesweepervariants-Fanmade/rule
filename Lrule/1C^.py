from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard, AbstractPosition, MASTER_BOARD

from .connect import connect

class Rule1C(AbstractMinesRule):
    id = "1C^"
    aliases = ("C^",)
    name = "Root"
    name.zh_CN = "树根"
    doc = "All mines form a tree root structure. The structure starts from one mine in the first row and extends downward, left-down, and right-down."
    doc.zh_CN = "所有雷形成一个树根结构。该结构是由第一行的一个雷开始向下、左下、右下延伸而成的。"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        col = board.get_config(config_name="size", board_key=MASTER_BOARD)[0]
        row = board.get_config(config_name="size", board_key=MASTER_BOARD)[1]

        root_vars = [model.NewBoolVar(f"root_{i}") for i in range(col * row)]

        connect(model, board, s,
                nei_value=lambda pos: [pos.up(), pos.up().left(), pos.up().right()],
                connect_value=1,
                root_vars=root_vars
        )

        model.Add(sum(root_vars[0:row]) == 1).OnlyEnforceIf(s)
        model.Add(sum(root_vars[row:]) == 0).OnlyEnforceIf(s)
        model.Add(sum(board.batch(board.get_row_pos(board.get_pos(0, 0)), mode="variable")) == 1).OnlyEnforceIf(s)
