"""
[2E'2U'] 自指列失衡：如果列 X 内有 N 个雷，则 X=N 所在的格子为雷。
"""

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board


class Rule2Ep2Up(AbstractMinesRule):
    id = "2E'2U'"
    name = "Self-Referential Column Imbalance"
    name.zh_CN = "自指列失衡"
    doc = "If column X contains N mines, the cell labelled X=N must be a mine."
    doc.zh_CN = "如果列 X 内有 N 个雷，则 X=N 所在的格子为雷"
    author = ("NT", 2201963934)
    tags = ["Original", "Global", "Construction"]
    creation_time = "2026-08-01"

    def __init__(self, board: Board | None = None, data: str | None = None) -> None:
        super().__init__(board, data)
        if board is None:
            return
        for key in board.get_interactive_keys():
            pos_bound = board.boundary(key)
            board.set_config(key, "pos_label", True)
            board.set_config(key, "labels", [str(i) for i in range(1, pos_bound.col + 2)])

    def create_constraints(self, board: Board, switch) -> None:
        model = board.get_model()
        rule_switch = switch.get(model, self)
        interactive_keys = board.get_interactive_keys()

        for key in interactive_keys:
            boundary = board.boundary(key)
            for column_pos in board.get_row_pos(boundary):
                column_vars = board.batch(
                    board.get_col_pos(column_pos),
                    mode="variable",
                )
                column_total = sum(column_vars)

                # N 等于列高时不存在 X=0 格，因此全雷列不满足规则。
                model.add(column_total != 0).only_enforce_if(
                    rule_switch
                )

                # 若 X=N 不是雷，则该列雷数不能为 N；这正是
                # “列雷数为 N => X=N 是雷”的逆否命题。
                for mine_count, target_var in enumerate(column_vars):
                    model.add(column_total != (mine_count + 1)).only_enforce_if(
                        [target_var.Not(), rule_switch]
                    )
