from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.impl.summon.solver import Switch

class RulePM(AbstractMinesRule):
    name = ["PM", "独一无二"]
    doc = "恰有一种方式从每行每列恰好选取一雷"

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)
        for key in board.get_interactive_keys():
            size = board.boundary(key).x + 1
            reduced_size = size
            last_vars = [var for _, var in board(mode="variable", key=key)]
            while reduced_size > 0:
                only_mine_var = model.NewIntVar(0, reduced_size - 1, f"[PM]only_mine_{key}_{reduced_size}")
                only_mine_flags = [model.NewBoolVar(f"[PM]only_mine_flag_{key}_{reduced_size}_{i}") for i in range(reduced_size)]
                for i in range(reduced_size):
                    model.Add(sum(last_vars[reduced_size * i:reduced_size * (i + 1)]) == 1).OnlyEnforceIf(only_mine_flags[i], s)
                    model.Add(sum(last_vars[reduced_size * i:reduced_size * (i + 1)]) != 1).OnlyEnforceIf(only_mine_flags[i].Not(), s)
                model.Add(sum(only_mine_flags) == 1).OnlyEnforceIf(s)
                model.AddElement(only_mine_var, only_mine_flags, 1)
                unique_mine_pos = model.NewIntVar(0, reduced_size - 1, f"[PM]unique_mine_pos_{key}_{reduced_size}")
                pos_index_var = model.NewIntVar(0, reduced_size * reduced_size - 1, f"[PM]pos_index_{key}_{reduced_size}")
                model.Add(pos_index_var == only_mine_var * reduced_size + unique_mine_pos).OnlyEnforceIf(s)
                model.AddElement(pos_index_var, last_vars, 1)

                reduced_size -= 1
                new_vars = [model.NewBoolVar(f"[PM]reduced_{key}_{reduced_size}_{i}") for i in range(reduced_size * reduced_size)]
                for i in range(len(new_vars)):
                    x = i // reduced_size
                    y = i % reduced_size
                    x_less_var = model.NewBoolVar(f"[PM]x_less_{key}_{reduced_size}_{i}")
                    y_less_var = model.NewBoolVar(f"[PM]y_less_{key}_{reduced_size}_{i}")
                    model.Add(x < only_mine_var).OnlyEnforceIf(x_less_var, s)
                    model.Add(x >= only_mine_var).OnlyEnforceIf(x_less_var.Not(), s)
                    model.Add(y < unique_mine_pos).OnlyEnforceIf(y_less_var, s)
                    model.Add(y >= unique_mine_pos).OnlyEnforceIf(y_less_var.Not(), s)

                    model.Add(new_vars[i] == last_vars[(reduced_size + 1) * x + y]).OnlyEnforceIf(x_less_var, y_less_var, s)
                    model.Add(new_vars[i] == last_vars[(reduced_size + 1) * (x + 1) + y]).OnlyEnforceIf(x_less_var.Not(), y_less_var, s)
                    model.Add(new_vars[i] == last_vars[(reduced_size + 1) * x + (y + 1)]).OnlyEnforceIf(x_less_var, y_less_var.Not(), s)
                    model.Add(new_vars[i] == last_vars[(reduced_size + 1) * (x + 1) + (y + 1)]).OnlyEnforceIf(x_less_var.Not(), y_less_var.Not(), s)
                last_vars = new_vars

