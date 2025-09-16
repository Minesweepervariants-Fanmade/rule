#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/09 03:33
# @Author  : Wu_RH
# @FileName: 2B.py
"""
[2B] 桥 (Bridge)：所有雷构成若干组桥。桥是从题版左边界八连通连接（水平或斜角连接）到右边界，宽度为 1、长度与题版相等的一条路径
"""
from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class Rule2B(AbstractMinesRule):
    name = ["2B", "桥", "Bridge"]
    doc = "所有雷构成若干组桥。桥是从题版左边界八连通连接（水平或斜角连接）到右边界，宽度为 1、长度与题版相等的一条路径"

    def create_constraints_(self, board: 'AbstractBoard', switch):
        def get_line_pos(pos):
            col = board.get_col_pos(pos)
            print("pos:", pos, "col:", col)
            if len(col) / 2 > col.index(pos):
                return col[:col.index(pos)][::-1], True
            else:
                return col[col.index(pos)+1:], False
        
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            pos_boundary = board.boundary(key=key)
            
            # 列平衡
            row_positions = board.get_row_pos(pos_boundary)
            row_sums = [
                sum(board.get_variable(_pos) for _pos in board.get_col_pos(pos))
                for pos in row_positions
            ]
            for i in range(1, len(row_sums)):
                model.Add(row_sums[i] == row_sums[0]).OnlyEnforceIf(s)
            
            for pos_row in board.get_row_pos(pos_boundary):
                print(board.get_col_pos(pos_row))
                for pos in board.get_col_pos(pos_row):
                    print("looking at", pos)
                    var = board.get_variable(pos)
                    col_pos, line_mode = get_line_pos(pos)
                    print(col_pos, line_mode)
                    if (
                        not col_pos and
                        not board.is_valid(pos.right().up() if line_mode else pos.right().down()) and
                        not board.is_valid(pos.left().up() if line_mode else pos.left().down())
                    ):
                        # 位置处于边界
                        if line_mode:
                            # 该位置位于上边界 
                            # 正中心为雷 或者正中心不是雷那么就下方是雷
                            if board.is_valid(pos.right()):
                                model.Add(board.get_variable(pos.right().down()) == 1).OnlyEnforceIf([
                                    var, s, board.get_variable(pos.right()).Not()
                                ])
                            elif board.is_valid(pos.right().down()):
                                model.Add(board.get_variable(pos.right().down()) == 1).OnlyEnforceIf([var, s])
                            if board.is_valid(pos.left()):
                                model.Add(board.get_variable(pos.left().down()) == 1).OnlyEnforceIf([
                                    var, s, board.get_variable(pos.left()).Not()
                                ])
                            elif board.is_valid(pos.left().down()):
                                model.Add(board.get_variable(pos.left().down()) == 1).OnlyEnforceIf([var, s])
                        else:
                            # 该位置位于下边界
                            # 正中心为雷 或者正中心不是雷那么就上方是雷
                            if board.is_valid(pos.right()):
                                model.Add(board.get_variable(pos.right().up()) == 1).OnlyEnforceIf([
                                    var, s, board.get_variable(pos.right()).Not()
                                ])
                            elif board.is_valid(pos.right().up()):
                                model.Add(board.get_variable(pos.right().up()) == 1).OnlyEnforceIf([var, s])
                            if board.is_valid(pos.left()):
                                model.Add(board.get_variable(pos.left().up()) == 1).OnlyEnforceIf([
                                    var, s, board.get_variable(pos.left()).Not()
                                ])
                            elif board.is_valid(pos.left().up()):
                                model.Add(board.get_variable(pos.left().up()) == 1).OnlyEnforceIf([var, s])
                        continue
                    
                    for x_pos in [
                        col_pos[0].left(),
                        col_pos[0].right()
                    ]:
                        if not board.is_valid(x_pos):
                            continue
                        tmp_a = model.NewBoolVar(f"tmp_a_{x_pos}")
                        tmp_b = model.NewBoolVar(f"tmp_b_{x_pos}")
                        tmp_c = model.NewBoolVar(f"tmp_c_{x_pos}")
                        x_col_pos, _ = get_line_pos(x_pos)
                        print(x_col_pos)
                        col_var = board.batch(col_pos, mode="variable")
                        x_col_var = board.batch(x_col_pos, mode="variable")
                        model.AddBoolOr([tmp_a, tmp_b, tmp_c]).OnlyEnforceIf([var, s])
                        model.Add(sum(col_var) == sum(x_col_var)).OnlyEnforceIf([tmp_a, var, s])
                        model.Add(
                            sum(col_var) == (
                                sum(x_col_var) +
                                board.get_variable(x_pos.down() if line_mode else x_pos.up())
                            )
                        ).OnlyEnforceIf([tmp_b, var, s])
                        model.Add(
                            sum(col_var) == (
                                sum(x_col_var) +
                                board.get_variable(
                                    x_pos.down() if line_mode else x_pos.up()
                                ) +
                                board.get_variable(
                                    x_pos.down(2) if line_mode else x_pos.up(2)
                                )
                            )
                        ).OnlyEnforceIf([tmp_c, var, s])
                        model.Add(tmp_a == 0).OnlyEnforceIf([board.get_variable(x_pos).Not()])
                        model.Add(tmp_b == 0).OnlyEnforceIf([
                            board.get_variable(x_pos.down() if line_mode else x_pos.up()).Not()
                        ])
                        model.Add(tmp_c == 0).OnlyEnforceIf([
                            board.get_variable(x_pos.down(2) if line_mode else x_pos.up(2)).Not()
                        ])
                        model.Add(
                            board.get_variable(x_pos) == 1
                        ).OnlyEnforceIf([tmp_a, var, s])
                        model.Add(board.get_variable(
                            x_pos.down() if line_mode else x_pos.up()
                        ) == 1).OnlyEnforceIf([tmp_b, var, s])
                        model.Add(board.get_variable(
                            x_pos.down(2) if line_mode else x_pos.up(2)
                        ) == 1).OnlyEnforceIf([tmp_c, var, s])

    def create_constraints(self, board: 'AbstractBoard', switch):
        """
        约束建议提供:哈嘿袁
        """
        # if self.get_name() == "2B:":
        #     return self.create_constraints_(board, switch)
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            boundary_pos = board.boundary(key=key)

            last_row = board.get_row_pos(boundary_pos)
            for index in range(len(last_row)):
                col_b = board.get_col_pos(last_row[index])
                col_var = []
                for index_t in range(len(col_b) - 1):
                    tmp_t = model.NewBoolVar(f"tmp_t_{col_b[index_t]}_{col_b[index_t + 1]}")
                    var_t_a = board.get_variable(col_b[index_t])
                    var_t_b = board.get_variable(col_b[index_t + 1])
                    model.AddBoolOr([var_t_a, var_t_b]).OnlyEnforceIf([tmp_t, s])
                    model.AddBoolAnd([var_t_a.Not(), var_t_b.Not()]).OnlyEnforceIf([tmp_t.Not(), s])
                    col_var.append(tmp_t)

                for index_a in range(len(col_b) - 1):
                    for index_b in range(index_a + 1, len(col_b)):
                        if -1 < index - 1 < len(last_row):
                            col_c = board.batch(board.get_col_pos(last_row[index - 1]), mode="variable")
                            model.Add(
                                sum(col_c[index_a+1:index_b]) ==
                                sum(board.batch(col_b[index_a+2:index_b-1], mode="variable"))
                            ).OnlyEnforceIf(col_var[index_a+1:index_b-1] +
                                            [col_var[index_a].Not(), col_var[index_b-1].Not(), s])
                        if -1 < index + 1 < len(last_row):
                            col_a = board.batch(board.get_col_pos(last_row[index + 1]), mode="variable")
                            model.Add(
                                sum(col_a[index_a+1:index_b]) ==
                                sum(board.batch(col_b[index_a+2:index_b-1], mode="variable"))
                            ).OnlyEnforceIf(col_var[index_a+1:index_b-1] +
                                            [col_var[index_a].Not(), col_var[index_b-1].Not(), s])

                for index_t in range(1, len(col_b) - 1):
                    if -1 < index - 1 < len(last_row):
                        col_c = board.batch(board.get_col_pos(last_row[index - 1]), mode="variable")
                        model.Add(
                            sum(col_c[:index_t+1]) ==
                            sum(board.batch(col_b[:index_t], mode="variable"))
                        ).OnlyEnforceIf(col_var[:index_t]+[col_var[index_t].Not(), s])
                    if -1 < index + 1 < len(last_row):
                        col_a = board.batch(board.get_col_pos(last_row[index + 1]), mode="variable")
                        model.Add(
                            sum(col_a[:index_t+1]) ==
                            sum(board.batch(col_b[:index_t], mode="variable"))
                        ).OnlyEnforceIf(col_var[:index_t]+[col_var[index_t].Not(), s])

                for index_t in range(1, len(col_b) - 1):
                    if -1 < index - 1 < len(last_row):
                        col_c = board.batch(board.get_col_pos(last_row[index - 1]), mode="variable")
                        model.Add(
                            sum(col_c[index_t:]) ==
                            sum(board.batch(col_b[index_t+1:], mode="variable"))
                        ).OnlyEnforceIf(col_var[index_t:] + [col_var[index_t-1].Not(), s])
                    if -1 < index + 1 < len(last_row):
                        col_a = board.batch(board.get_col_pos(last_row[index + 1]), mode="variable")
                        model.Add(
                            sum(col_a[index_t:]) ==
                            sum(board.batch(col_b[index_t+1:], mode="variable"))
                        ).OnlyEnforceIf(col_var[index_t:] + [col_var[index_t-1].Not(), s])

            # 两个并排的非雷其上下两侧的雷数必然相同
            for pos in board.get_col_pos(boundary_pos):
                row = board.get_row_pos(pos)
                for index in range(len(row) - 1):
                    pos_a, pos_b = row[index], row[index + 1]
                    var_a, var_b = board.batch([pos_a, pos_b], mode="variable")
                    line_a = board.get_col_pos(pos_a)
                    line_a = line_a[:line_a.index(pos_a)]
                    line_b = board.get_col_pos(pos_b)
                    line_b = line_b[:line_b.index(pos_b)]
                    vars_a = board.batch(line_a, mode="variable")
                    vars_b = board.batch(line_b, mode="variable")
                    model.Add(sum(vars_a) == sum(vars_b)).OnlyEnforceIf([var_a.Not(), var_b.Not(), s])

            # 列平衡
            row_positions = board.get_row_pos(boundary_pos)
            row_sums = [
                sum(board.get_variable(_pos) for _pos in board.get_col_pos(pos))
                for pos in row_positions
            ]
            # 所有 row_sums 相等
            for i in range(1, len(row_sums)):
                model.Add(row_sums[i] == row_sums[0]).OnlyEnforceIf(s)

    def suggest_total(self, info: dict):
        size_list = [info["size"][key] for key in info["interactive"]]

        def a(model, total):
            nonlocal size_list
            var_list = []
            for i, (height, width) in enumerate(size_list):
                n = model.NewIntVar(0, height * width, f"width_{i}")
                model.AddModuloEquality(0, n, width)
                var_list.append(n)
            model.Add(sum(var_list) == total)

        info["hard_fns"].append(a)
