"""
[EST-L2] TEST-L2: 每一行各有一组连续的雷，且各行数量均不同
"""
from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class Rule(AbstractMinesRule):
    name = ["TEST-L2", "TEST-L2"]
    doc = "每一行各有一组连续的雷且数量各不相同"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            pos_bound = board.boundary(key)
            row_lengths = []

            # 逐行处理：确保每行恰有一个连续的雷段，并记录长度
            for col_pos in board.get_col_pos(pos_bound):
                row = board.get_row_pos(col_pos)
                vars_row = board.batch(row, mode="variable")

                # 至少有一个雷（有段）
                model.AddBoolOr(vars_row).OnlyEnforceIf(s)

                # 仅一段：当出现 1->0 时，后续全为 0；当出现 0->1 时，之前全为 0
                for index, var in enumerate(vars_row[:-1]):
                    model.Add(sum(vars_row[index + 1:]) == 0).OnlyEnforceIf([var, vars_row[index + 1].Not(), s])
                for index, var in enumerate(vars_row[1:]):
                    model.Add(sum(vars_row[:index + 1]) == 0).OnlyEnforceIf([var, vars_row[index].Not(), s])

                # 记录该行雷段长度（在仅一段的前提下，长度等于该行雷数量）
                row_lengths.append(sum(vars_row))

            # 不同行的雷段长度两两不同
            for i in range(len(row_lengths)):
                for j in range(i + 1, len(row_lengths)):
                    model.Add(row_lengths[i] != row_lengths[j]).OnlyEnforceIf(s)

    def suggest_total(self, info: dict):
        # 目标总雷数：各行连续段长度互不相同，且每行至少一个雷。
        # 在宽度足够的前提下，最小可行总雷数为 1+2+...+rows = rows*(rows+1)//2。
        target = 0
        for key in info["interactive"]:
            w, h = info["size"][key]
            k = min(w, h)  # 宽度不足会导致不可行，这里取较小值作为保守建议
            target += k * (k + 1) // 2
        # 建议优先级设为 1：较高优先以避免与规则冲突的总雷数
        info["soft_fn"](target, 1)
