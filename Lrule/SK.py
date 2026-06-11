from ortools.sat.python.cp_model import IntVar


from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.size import Size
from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board


class RuleSK(AbstractMinesRule):
    id = "SK"
    name = "Delete"
    name.zh_CN = "删除"
    doc = "Each row is obtained by deleting two consecutive cells from the previous row, shifting all cells to the right of the deleted cells two positions to the left, and then adding any two cells at the end."
    doc.zh_CN = "每行都是由上一行删除连续的两个格，其右方所有格向左方平移两格，然后末尾补上任意两个格得到的。"
    tags = ["Creative", "Global"]
    creation_time = "2026-05-27"
    author = ("NT", 2201963934)

    def __init__(self, board: "Board", data: str | None):
        super().__init__()
        key = board.get_interactive_keys()[0]
        size = board.get_config(key, "size")
        assert isinstance(size, Size)

        if isinstance(data, str) and '!' in data:
            self.sub_board = True
            board.generate_board("SK", size=Size(size.cols, size.rows))
        else:
            self.sub_board = False

    def init_clear(self, board: "Board"):
        if self.sub_board:
            for pos, _ in board(key="SK"):
                if pos.row < board.get_config("SK", "size").rows - 1:
                    board.set_value(pos, None)

    def create_constraints(self, board: 'Board', switch: Switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            boundary_pos = board.boundary(key=key)
            _row, col = boundary_pos.row + 1, boundary_pos.col + 1
            col_positions = board.get_col_pos(boundary_pos)

            if self.sub_board:
                for i, row_end in enumerate(col_positions):
                    row_end_sk_pos = row_end.clone()
                    row_end_sk_pos.to_board("SK")
                    row_sk_var: list[IntVar] = [var for pos in (board.get_row_pos(row_end_sk_pos))
                                                    if (var := board.get_variable(pos)) is not None]
                    for v1, v2, v3 in zip(row_sk_var, row_sk_var[1:], row_sk_var[2:]):
                        model.add_bool_xor([v1, v3]).only_enforce_if(v2)
                    model.add(row_sk_var[1] == 1).only_enforce_if(row_sk_var[0])
                    model.add(row_sk_var[-2] == 1).only_enforce_if(row_sk_var[-1])

                    if i < len(col_positions) - 1:
                        model.add(sum(row_sk_var) == 2)
                    else:
                        model.add(sum(row_sk_var) == 0)

            for row_end in col_positions[:-1]:
                next_row_end = row_end.down()
                row_var: list[IntVar] = [
                    var for pos in board.get_row_pos(row_end)
                        if (var := board.get_variable(pos)) is not None
                    ]

                delete_idx = (model.new_int_var(0, col - 2, f"{key}_delete_idx_{row_end}"))

                for i, pos in enumerate(board.get_row_pos(next_row_end)[:-2]):
                    up_idx = model.new_int_var(0, col - 1, f"{key}_up_idx_{pos}")
                    before_idx = model.new_bool_var(f"{key}_before_idx_{pos}")

                    if self.sub_board:
                        sk_pos = pos.clone().up()
                        sk_pos.to_board("SK")
                        sk_var = board.get_variable(sk_pos)
                        sk_var_right = board.get_variable(sk_pos.right())

                        assert sk_var is not None
                        assert sk_var_right is not None

                        del_var = model.new_bool_var(f"{key}_del_var_{pos}")
                        model.add(i == delete_idx).only_enforce_if(del_var)
                        model.add(i != delete_idx).only_enforce_if(~del_var)

                        model.add_bool_and(sk_var, sk_var_right).only_enforce_if([del_var, s])
                        model.add_bool_or(sk_var.Not(), sk_var_right.Not()).only_enforce_if([~del_var, s])


                    model.add(i < delete_idx).only_enforce_if(before_idx)
                    model.add(i >= delete_idx).only_enforce_if(~before_idx)

                    model.add(up_idx == i).only_enforce_if(before_idx)
                    model.add(up_idx == i + 2).only_enforce_if(~before_idx)

                    target = board.get_variable(pos)
                    if target is None:
                        continue

                    model.add_element(index=up_idx,
                                      expressions=row_var,
                                      target=target) \
                         .only_enforce_if(s)
