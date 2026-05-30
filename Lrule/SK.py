from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class RuleSK(AbstractMinesRule):
    id = "SK"
    name = "Delete"
    name.zh_CN = "删除"
    doc = "Each row is obtained by deleting two consecutive cells from the previous row, shifting all cells to the right of the deleted cells two positions to the left, and then adding any two cells at the end."
    doc.zh_CN = "每行都是由上一行删除连续的两个格，其右方所有格向左方平移两格，然后末尾补上任意两个格得到的。"
    tags = ["Creative", "Global"]
    creation_time = "2026-05-27"
    author = ("NT", 2201963934)

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            boundary_pos = board.boundary(key=key)
            row, col = boundary_pos.row, boundary_pos.col
            col_positions = board.get_col_pos(boundary_pos)

            for row_end in col_positions[:-1]:
                next_row_end = row_end.down()
                row_var = [board.get_variable(var) for var in board.get_row_pos(row_end)]

                delete_idx = (model.new_int_var(0, col - 1, f"{key}_delete_idx_{row_end}"))

                for i, pos in enumerate(board.get_row_pos(next_row_end)[:-2]):
                    up_idx = model.new_int_var(0, col, f"{key}_up_idx_{pos}")
                    before_idx = model.new_bool_var(f"{key}_before_idx_{pos}")

                    model.add(i < delete_idx).only_enforce_if(before_idx)
                    model.add(i >= delete_idx).only_enforce_if(~before_idx)

                    model.add(up_idx == i).only_enforce_if(before_idx)
                    model.add(up_idx == i + 2).only_enforce_if(~before_idx)
                    model.add_element(up_idx, row_var, board.get_variable(pos)).only_enforce_if(s)
