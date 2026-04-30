from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard, AbstractPosition

def block(a_pos: AbstractPosition, board: AbstractBoard) -> list[AbstractPosition]:
    b_pos = a_pos.up()
    c_pos = a_pos.left()
    d_pos = b_pos.left()
    if not board.in_bounds(d_pos):
        return []
    return [a_pos, b_pos, c_pos, d_pos]

class RuleCL(AbstractMinesRule):
    name = ["CL", "海岸线", "Coastline"]
    doc = "雷区域与非雷区域之间不存在长度大于等于 2 的直线分界线"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        for pos, _ in board():
            pos_list = block(pos, board)
            if not pos_list:
                continue
            a, b, c, d = board.batch(pos_list, mode="variable")
            model.AddBoolOr([a, b.Not(), c, d.Not()]).OnlyEnforceIf(s) # 排除 0101
            model.AddBoolOr([a.Not(), b, c.Not(), d]).OnlyEnforceIf(s) # 排除 1010
            model.AddBoolOr([a, b, c.Not(), d.Not()]).OnlyEnforceIf(s) # 排除 0011
            model.AddBoolOr([a.Not(), b.Not(), c, d]).OnlyEnforceIf(s) # 排除 1100
