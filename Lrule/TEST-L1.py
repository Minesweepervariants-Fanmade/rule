"""
[TEST-L1] TEST-L1：如果一个格子是雷，其水平对称格不是雷
"""
from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class Rule1HX(AbstractMinesRule):
    name = ["TEST-L1", "TEST-L1"]
    doc = "如果一个格子是雷，其水平对称格不是雷"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            pos_bound = board.boundary(key)
            # 遍历所有格子对
            for index_x in range(pos_bound.x + 1):
                for index_y in range(pos_bound.y + 1):
                    var = board.get_variable(board.get_pos(index_x, index_y, key))
                    # 水平对称位置：改变y坐标（因为坐标系统中x和y在某些地方是反的）
                    var_mirror = board.get_variable(board.get_pos(index_x, pos_bound.y - index_y, key))

                    if var is not None and var_mirror is not None:
                        # 如果当前格子是雷，则对称格子不能是雷
                        # 即：var == 1 => var_mirror == 0
                        # 逻辑等价于：(var == 0) OR (var_mirror == 0)
                        model.AddBoolOr([var.Not(), var_mirror.Not()]).OnlyEnforceIf(s)
