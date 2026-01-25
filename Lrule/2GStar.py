"""
[2G*] 互异四连块：(1) 所有四连通雷区域的面积为 4 (2) 且它们形状不同（SZ 和 JL 型视为相同形状）
"""
from typing import Callable
from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard, AbstractPosition
from ..sharpRule.Csharp import FakeSwitch
from importlib import import_module

rule2G = import_module("minesweepervariants.impl.rule.Lrule.2G")

def nei_pos_I(pos: AbstractPosition) -> list[list[AbstractPosition]]:
    return [
        [pos.down(1), pos.down(2), pos.down(3)],
        [pos.right(1), pos.right(2), pos.right(3)],
    ]

def nei_pos_O(pos: AbstractPosition) -> list[list[AbstractPosition]]:
    return [
        [pos.down(1), pos.down(1).right(1), pos.right(1)],
    ]

def nei_pos_T(pos: AbstractPosition) -> list[list[AbstractPosition]]:
    return [
        [pos.down(1), pos.down(2), pos.down(1).right(1)],
        [pos.down(1), pos.down(2), pos.down(1).left(1)],
        [pos.right(1), pos.right(2), pos.right(1).up(1)],
        [pos.right(1), pos.right(2), pos.right(1).down(1)],
    ]

def nei_pos_L(pos: AbstractPosition) -> list[list[AbstractPosition]]:
    return [
        [pos.down(1), pos.down(2), pos.right(1)],
        [pos.down(1), pos.down(2), pos.left(1)],
        [pos.right(1), pos.right(2), pos.up(1)],
        [pos.right(1), pos.right(2), pos.down(1)],
        [pos.down(1), pos.down(2), pos.down(2).right(1)],
        [pos.down(1), pos.down(2), pos.down(2).left(1)],
        [pos.right(1), pos.right(2), pos.right(2).up(1)],
        [pos.right(1), pos.right(2), pos.right(2).down(1)],
    ]

def nei_pos_S(pos: AbstractPosition) -> list[list[AbstractPosition]]:
    return [
        [pos.right(1), pos.right(1).down(1), pos.right(2).down(1)],
        [pos.right(1), pos.right(1).up(1), pos.right(2).up(1)],
        [pos.down(1), pos.down(1).right(1), pos.down(2).right(1)],
        [pos.down(1), pos.down(1).left(1), pos.down(2).left(1)],
    ]

class Rule2GStar(AbstractMinesRule):
    name = ["2G*", "互异四连块", "Group*"]
    doc = "(1) 所有四连通雷区域的面积为 4 (2) 且它们形状不同（SZ 和 JL 型视为相同形状）"

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)

    def create_constraints(self, board: AbstractBoard, switch):
        def at_most_one_shape(board: AbstractBoard, nei_pos_func: Callable[[AbstractPosition], list[list[AbstractPosition]]], switch_var):
            vars = []
            model = board.get_model()
            for pos, mine_var in board("always", mode="variable"):
                nei_poses = [nei_pos for nei_pos in nei_pos_func(pos) if all(board.in_bounds(i) for i in nei_pos)]
                if not nei_poses:
                    continue
                shape_var = model.NewBoolVar("shape")
                vars.append(shape_var)
                nei_pos_vars = []
                for nei_pos in nei_poses:
                    nei_pos_var = model.NewBoolVar("nei_pos_var")
                    nei_pos_vars.append(nei_pos_var)
                    model.Add(sum(board.batch(nei_pos, mode="variable")) == 3).OnlyEnforceIf([mine_var, nei_pos_var, switch_var])
                    model.Add(sum(board.batch(nei_pos, mode="variable")) != 3).OnlyEnforceIf([mine_var, nei_pos_var.Not(), switch_var])
                model.Add(sum(nei_pos_vars) == 1).OnlyEnforceIf([mine_var, shape_var, switch_var])
                model.Add(sum(nei_pos_vars) != 1).OnlyEnforceIf([mine_var, shape_var.Not(), switch_var])
                model.Add(shape_var == 0).OnlyEnforceIf([mine_var.Not(), switch_var])
            model.Add(sum(vars) <= 1).OnlyEnforceIf(switch_var)

        model = board.get_model()
        s1 = switch.get(model, self)
        s2 = switch.get(model, self)
        rule2G.Rule2G(board).create_constraints(board, FakeSwitch(s1))
        at_most_one_shape(board, nei_pos_I, s2)
        at_most_one_shape(board, nei_pos_O, s2)
        at_most_one_shape(board, nei_pos_T, s2)
        at_most_one_shape(board, nei_pos_L, s2)
        at_most_one_shape(board, nei_pos_S, s2)

    def suggest_total(self, info: dict):

        def hard_constraint(m, total):
            m.AddModuloEquality(0, total, 4)
            m.Add(total <= 20)

        ub = 0
        for key in info["interactive"]:
            total = info["total"][key]
            ub += total
        
        info["soft_fn"](ub * 0.335, 0)
        info["hard_fns"].append(hard_constraint)
