"""
[2E'2U'] 自指列失衡：如果列 X 内有 N 个雷，则 X=N 所在的格子为雷。
"""

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.utils.tool import get_random


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
            board.set_config(key, "pos_label", True)

    def create_constraints(self, board: Board, switch) -> None:
        model = board.get_model()
        rule_switch = switch.get(model, self)
        interactive_keys = board.get_interactive_keys()
        hint_empty_board = all(
            cell_type == "N"
            for key in interactive_keys
            for _, cell_type in board(mode="type", key=key, special="raw")
        )
        random = get_random() if hint_empty_board else None
        hinted_variables = (
            set(model.proto.solution_hint.vars) if hint_empty_board else set()
        )

        for key in interactive_keys:
            boundary = board.boundary(key)
            for column_pos in board.get_row_pos(boundary):
                column_vars = board.batch(
                    board.get_col_pos(column_pos),
                    mode="variable",
                )
                column_total = sum(column_vars)

                # N 等于列高时不存在 X=N 格，因此全雷列不满足规则。
                model.add(column_total != len(column_vars)).only_enforce_if(
                    rule_switch
                )

                # 若 X=N 不是雷，则该列雷数不能为 N；这正是
                # “列雷数为 N => X=N 是雷”的逆否命题。
                for mine_count, target_var in enumerate(column_vars):
                    model.add(column_total != mine_count).only_enforce_if(
                        [target_var.Not(), rule_switch]
                    )

                # 提示一个随机的合法列布局，避免高度对称的模型在不同种子下
                # 总落到同一个解。hint 不属于约束，因此不改变规则的可行解集。
                if random is not None and len(column_vars) > 1:
                    hinted_count = min(
                        max(round(len(column_vars) * 0.4), 1),
                        len(column_vars) - 1,
                    )
                    other_indices = [
                        index for index in range(len(column_vars))
                        if index != hinted_count
                    ]
                    hinted_mines = {hinted_count}
                    hinted_mines.update(
                        random.sample(other_indices, hinted_count - 1)
                    )
                    for index, var in enumerate(column_vars):
                        if var.index not in hinted_variables:
                            model.add_hint(var, int(index in hinted_mines))
                            hinted_variables.add(var.index)
