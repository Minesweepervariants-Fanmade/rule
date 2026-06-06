#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
[3Q~] 所有四连通的非雷格区域组成实心正方形
基于 3Q 规则（雷区域组成实心正方形）的雷/非雷互换实现。
"""

from typing import List

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board, Position
from ....impl.summon.solver import Switch


def block(a_pos: Position, board: Board) -> List[Position]:
    b_pos = a_pos.up()
    c_pos = a_pos.left()
    d_pos = b_pos.left()
    if not board.in_bounds(d_pos):
        return []
    return [a_pos, b_pos, c_pos, d_pos]


class Rule3Q(AbstractMinesRule):
    id = "3Q~"
    name = "3Q~"
    name.zh_CN = "非雷正方"
    doc = "All 4-connected non-mine regions form solid squares"
    doc.zh_CN = "所有四连通的非雷格区域组成实心正方形"
    tags = ["Variant", "Connectivity", "Strict Shape"]
    creation_time = "2026-03-01"
    author = ("波常未来", 81500378)

    def create_constraints(self, board: 'Board', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)

        # 将原 3Q 规则中的雷变量取反，使其表示非雷
        for pos, var in board(mode="var"):
            # 非雷变量 = 1 - var
            not_mine_var = model.new_bool_var(f"not_mine_{pos.x}_{pos.y}")
            model.add(not_mine_var == 1 - var)

            block_pos = block(pos, board)
            if block_pos:
                # 原规则：model.add(sum(block_var) != 3)
                # 现在 block_var 是雷变量，需要转换为非雷变量
                block_not_mine_vars = []
                for p in block_pos:
                    nmv = model.new_bool_var(f"not_mine_block_{p.x}_{p.y}")
                    model.add(nmv == 1 - board.get_variable(p))
                    block_not_mine_vars.append(nmv)
                model.add(sum(block_not_mine_vars) != 3).OnlyEnforceIf(s)

            row = board.get_row_pos(pos)
            col = board.get_col_pos(pos)

            var_list = [not_mine_var]
            if board.in_bounds(pos.up()):
                up_var = model.new_bool_var(f"not_mine_up_{pos.x}_{pos.y}")
                model.add(up_var == 1 - board.get_variable(pos.up()))
                var_list.append(up_var.Not())
            if board.in_bounds(pos.left()):
                left_var = model.new_bool_var(f"not_mine_left_{pos.x}_{pos.y}")
                model.add(left_var == 1 - board.get_variable(pos.left()))
                var_list.append(left_var.Not())

            tmp_list = []

            for row_pos, col_pos in zip(
                row[row.index(pos):],
                col[col.index(pos):]
            ):
                tmp = model.new_bool_var(f"tmp[{pos}, {row_pos}, {col_pos}]")
                model.add_bool_and(var_list).OnlyEnforceIf(tmp)
                row_box = board.get_pos_box(pos, row_pos)
                col_box = board.get_pos_box(pos, col_pos)
                # 转换 row_box 和 col_box 中的变量为非雷变量
                row_not_mine_vars = []
                for p in row_box:
                    rnmv = model.new_bool_var(f"not_mine_row_{p.x}_{p.y}")
                    model.add(rnmv == 1 - board.get_variable(p))
                    row_not_mine_vars.append(rnmv)
                col_not_mine_vars = []
                for p in col_box:
                    cnmv = model.new_bool_var(f"not_mine_col_{p.x}_{p.y}")
                    model.add(cnmv == 1 - board.get_variable(p))
                    col_not_mine_vars.append(cnmv)
                model.add_bool_and(row_not_mine_vars).OnlyEnforceIf(tmp)
                model.add_bool_and(col_not_mine_vars).OnlyEnforceIf(tmp)
                if board.is_valid(row_pos.right()):
                    right_var = model.new_bool_var(f"not_mine_right_{row_pos.x}_{row_pos.y}")
                    model.add(right_var == 1 - board.get_variable(row_pos.right()))
                    model.add_bool_and(right_var.Not()).OnlyEnforceIf(tmp)
                if board.is_valid(col_pos.down()):
                    down_var = model.new_bool_var(f"not_mine_down_{col_pos.x}_{col_pos.y}")
                    model.add(down_var == 1 - board.get_variable(col_pos.down()))
                    model.add_bool_and(down_var.Not()).OnlyEnforceIf(tmp)
                tmp_list.append(tmp)
            model.add_bool_or(tmp_list).OnlyEnforceIf(var_list + [s])
