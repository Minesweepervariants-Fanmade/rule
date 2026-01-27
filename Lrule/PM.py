from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.impl.summon.solver import Switch

from itertools import permutations

def possible_selections(n: int) -> list[list[tuple[int, int]]]:
    perms = permutations(range(n), n)
    return [[(i, perm[i]) for i in range(n)] for perm in perms]


class RulePM(AbstractMinesRule):
    name = ["PM", "独一无二"]
    doc = "恰有一种方式从每行每列恰好选取一雷"

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)
        for key in board.get_interactive_keys():
            size = board.boundary(key).x + 1
            #TODO: O(n!)，能优化吗，我不知道，也许可以套两个 SAT model?
            selections = possible_selections(size)
            selection_vars = [model.NewBoolVar(f"[PM]sel{idx}") for idx in range(len(selections))]
            for idx, selection in enumerate(selections):
                poses = [board.get_pos(i, j, key) for i, j in selection]
                model.Add(sum(board.batch(poses, mode="variable")) == size).OnlyEnforceIf(selection_vars[idx], s)
                model.Add(sum(board.batch(poses, mode="variable")) != size).OnlyEnforceIf(selection_vars[idx].Not(), s)
            model.Add(sum(selection_vars) == 1).OnlyEnforceIf(s)

