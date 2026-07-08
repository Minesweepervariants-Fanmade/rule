#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/16 09:20
# @Author  : xxx
# @FileName: 2A.py
"""
[2A]面积: 线索表示四方向相邻雷区域的面积之和
(注:如果出现大数字则速率极度底下)
"""
from typing import List, Tuple, Optional, Self, cast

from minesweepervariants.abs.rule import AbstractRule
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.utils.impl_obj import POSITION_TAG
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.utils.value_template import SingleIntValue, Template
from minesweepervariants.board import Board, Position

from ....utils.tool import get_logger


UN_FLAG = 0
GROUP_4 = 1
GROUP_3 = 2
CONNECT = 4

ID_2A = "ID_2A"
COUNT_2A = "COUNT_2A"
DEBUG = False


class Data2A(SingleIntValue):
    def __init__(self, value: int, value_type):
        super().__init__(value, False)
        self.value_type = value_type

    def _template(self) -> Template:
        result = super()._template()
        result["_SingleIntValue"] = True
        result["data"] = self.value
        result["value_type"] = self.value_type
        return result

    @classmethod
    def try_from(cls, data: Template) -> Self | None:
        if not data.get("_SingleIntValue", False):
            return None

        value = cast(int, data["data"])
        value_type = cast(int, data["value_type"])

        return cls(value, value_type)

    def __eq__(self, __value: int):
        return self.value == __value

    def __ne__(self, __value: int):
        return self.value != __value

    def __lt__(self, __value: int):
        return self.value < __value

    def __gt__(self, __value: int):
        return self.value > __value


def pos2seed(input_pos: Position, board: Board) -> int:
    bound = board.boundary(input_pos.board_key)
    offset = 0
    for board_key in board.get_board_keys():
        if board_key == input_pos.board_key:
            break
        offset += len([pos for pos, _ in board(key=board_key)])
    return input_pos.row * (bound.col + 1) + input_pos.col + 1 + offset


def seed2pos(input_seed: int, board: Board) -> Position:
    board_key = None
    for board_key in board.get_board_keys():
        total = len([pos for pos, _ in board(key=board_key)])
        if input_seed < total:
            break
        input_seed -= total
    if board_key is None:
        return POSITION_TAG
    bound = board.boundary(board_key)
    return board.get_pos(
        (input_seed - 1) // (bound.col + 1),
        (input_seed - 1) % (bound.col + 1),
        board_key
    )


class Rule2A(AbstractClueRule):
    id = "2A"
    name = "Area"
    name.zh_CN = "面积"
    doc = "Clue indicates the sum of areas of orthogonally adjacent mine groups"
    doc.zh_CN = "线索表示四方向相邻雷区域的面积之和"
    tags = ["Variant", "Local", "Number Clue", "Extensive Trial", "Weak"]
    creation_time = "2025-08-06"
    author = ("", 0)

    def __init__(self, board: "Board" = None, data=None):
        super().__init__(board, data)
        self.debug_vars = {}
        self.flag = UN_FLAG

    def combine(self, rules: List[Tuple['AbstractRule', Optional[str]]]):
        """
        合并规则：
        - 如果存在 (rule, data)，其中 rule 的 name 是 '1S'
        - 并且 data 满足以下之一：
            * None
            * "1"
            * "1;1;...;1"（由一个或多个 '1' 组成，中间以分号分隔）
        则将 self.flag_1S 设为 True。
        """
        for rule, data in rules:
            name = getattr(rule, "name", None)
            if isinstance(name, list):
                name = name[0] if name else None

            if (name in ["1S", "3Y", "1S'", "1S^"] and
               (data is None or all(x == "1" or "1:1" in x for x in data.split(";")))):
                self.flag = CONNECT

            if name == "2G" and data is None:
                self.flag = GROUP_4

            if name == "2G'" and data is None:
                self.flag = GROUP_3

    def fill(self, board: 'Board') -> 'Board':
        logger = get_logger()
        for pos, _ in board("N"):
            if self.flag == CONNECT:
                if board.batch(pos.neighbors(1), "type").count("F") > 0:
                    board.set_value(pos, Value2A(pos, CONNECT, 1))
                else:
                    board.set_value(pos, Value2A(pos, CONNECT, 0))
                continue
            checked = [[False for _ in range(20)] for _ in range(20)]

            def dfs(p: 'Position', _checked):
                if not board.in_bounds(p): return None
                if board.get_type(p) != "F": return None
                if _checked[p.row][p.col]: return None
                _checked[p.row][p.col] = True
                dfs(p.left(1), _checked)
                dfs(p.right(1), _checked)
                dfs(p.up(1), _checked)
                dfs(p.down(1), _checked)
                return None

            dfs(pos.left(1), checked)
            dfs(pos.right(1), checked)
            dfs(pos.up(1), checked)
            dfs(pos.down(1), checked)
            cnt = 0
            for i in range(20):
                for j in range(20):
                    if checked[i][j]:
                        cnt += 1
            board.set_value(pos, Value2A(pos, self.flag, cnt))
            logger.debug(f"Set {pos} to 2A[{cnt}]")
        return board

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        if self.flag != UN_FLAG:
            return

        max_var = len([pos for pos, _ in board()])
        id_vars = {pos: model.new_int_var(0, max_var, f"id_{pos}") for pos, _ in board()}
        step_vars = {pos: model.new_int_var(0, max_var, f"step_{pos}") for pos, _ in board()}

        for pos, _ in board():
            pos_var = board.get_variable(pos)
            is_root = model.new_bool_var(f"{pos}_is_root")
            nei1_poses = [nei_pos for nei_pos in pos.neighbors(1, 1) if nei_pos in id_vars]
            for nei_pos in nei1_poses:
                # 相邻两格必须id相同
                model.add(id_vars[nei_pos] == id_vars[pos]).OnlyEnforceIf(
                    board.get_variable(pos), board.get_variable(nei_pos)
                )

            # 如果该格是雷
            model.add(id_vars[pos] > 0).only_enforce_if(pos_var)
            model.add(step_vars[pos] > 0).only_enforce_if(pos_var)
            model.add(pos_var == 1).only_enforce_if(is_root)

            # 该格是雷且是root
            model.add(step_vars[pos] == max_var).only_enforce_if(pos_var, is_root)
            model.add(id_vars[pos] == pos2seed(pos, board)).only_enforce_if(pos_var, is_root)

            # 该格是雷且不是root
            model.add(id_vars[pos] > pos2seed(pos, board)).only_enforce_if(pos_var, is_root.Not())

            # 取周围最大的step-1
            model.add_max_equality(
                step_vars[pos],
                [step_vars[nei_pos] - 1 for nei_pos in nei1_poses],
            ).OnlyEnforceIf(pos_var, is_root.Not())
            for nei_pos in nei1_poses:
                tmp_var = model.new_bool_var("")
                model.add(step_vars[pos] == step_vars[nei_pos] - 1).OnlyEnforceIf(tmp_var)
                model.add(step_vars[pos] != step_vars[nei_pos] - 1).OnlyEnforceIf(tmp_var.Not())
                model.add(id_vars[pos] == id_vars[nei_pos]).only_enforce_if(pos_var, tmp_var, is_root.Not())

            # 如果该格非雷
            model.add(id_vars[pos] == 0).only_enforce_if(pos_var.Not())
            model.add(step_vars[pos] == 0).only_enforce_if(pos_var.Not())
            model.add(is_root == 0).only_enforce_if(pos_var.Not())
            if DEBUG:
                self.debug_vars[is_root.name] = is_root

        count_vars = {}
        for seed_id in range(1, max_var + 1):
            count_var = model.new_int_var(0, max_var, f"id{seed_id}Cound")
            count_vars[seed_id] = count_var
            sum_vars = []
            for pos, _ in board():
                tmp_var = model.new_bool_var(f"{pos}={seed_id}")
                model.add(id_vars[pos] == seed_id).only_enforce_if(tmp_var)
                model.add(id_vars[pos] != seed_id).only_enforce_if(tmp_var.Not())
                sum_vars.append(tmp_var)
            model.add(count_var == sum(sum_vars))

        if DEBUG:
            self.debug_vars.update({var.name: var for var in id_vars.values()})
            self.debug_vars.update({var.name: var for var in count_vars.values()})
            self.debug_vars.update({var.name: var for var in step_vars.values()})

        for pos, var in id_vars.items():
            board.register_variable_special(ID_2A, pos, var)

        for seed, var in count_vars.items():
            board.register_variable_special(COUNT_2A, seed2pos(seed, board), var)


class Value2A(AbstractClueValue):
    id = Rule2A.id

    def __init__(self, pos: 'Position', value_type: int, value: int):
        super().__init__(pos)
        self.debug_vars = {}
        self.value: Data2A = Data2A(value, value_type)
        self.value_type = value_type

    @classmethod
    def from_json(cls, pos: 'Position', data: 'Template') -> Self:
        value_data = Data2A.try_from(data)
        return cls(pos, value_data.value_type, value_data.value)

    def create_constraints_connect(self, model, board, switch):
        var_list = board.batch(self.pos.neighbors(1), "var", drop_none=True)
        if self.value == 0:
            model.add_bool_and([var.Not() for var in var_list]).OnlyEnforceIf(switch)
        model.add_bool_or(var_list).OnlyEnforceIf(switch)

    def create_constraints_group_4(self, model, board, s):
        if self.value.value % 4 != 0:
            model.Add(s == 0)
            return
        value = self.value.value // 4
        return self.create_constraints_group(value, model, board, s)

    def create_constraints_group_3(self, model, board, s):
        if self.value.value % 3 != 0:
            model.Add(s == 0)
            return
        value = self.value.value // 3
        return self.create_constraints_group(value, model, board, s)

    def create_constraints_group(self, value, model, board, s):
        var_a = board.get_variable(self.pos.up().left())
        var_b = board.get_variable(self.pos.up().right())
        var_c = board.get_variable(self.pos.down().right())
        var_d = board.get_variable(self.pos.down().left())

        var_1 = board.get_variable(self.pos.up())
        var_2 = board.get_variable(self.pos.right())
        var_3 = board.get_variable(self.pos.down())
        var_4 = board.get_variable(self.pos.left())

        var_dict = {}
        """
        A 1 B
        4 ? 2
        D 3 C
        """

        for __var_1, __var_2, __var_3, ap_n in [
            (var_a, var_1, var_4, "A"),
            (var_b, var_1, var_2, "B"),
            (var_c, var_3, var_2, "C"),
            (var_d, var_3, var_4, "D"),
        ]:
            if __var_1 is None or __var_2 is None or __var_3 is None:
                continue
            var_X = model.NewBoolVar(f"{__var_1}")
            model.Add(var_X == 1).OnlyEnforceIf([__var_1, __var_2, __var_3])
            model.Add(var_X == 0).OnlyEnforceIf(__var_1.Not())
            model.Add(var_X == 0).OnlyEnforceIf(__var_2.Not())
            model.Add(var_X == 0).OnlyEnforceIf(__var_3.Not())
            var_dict[ap_n] = var_X

        for var_n, ap_1, ap_2 in [
            (var_1, "A", "B"),
            (var_2, "C", "B"),
            (var_3, "D", "C"),
            (var_4, "A", "D"),
        ]:
            if var_n is None:
                continue
            if ap_1 not in var_dict and ap_2 not in var_dict:
                Var_n = var_n
            elif ap_1 not in var_dict:
                Var_n = model.NewBoolVar(f"{var_n}")
                model.Add(Var_n == var_n).OnlyEnforceIf(var_dict[ap_2].Not())
                model.Add(Var_n == 0).OnlyEnforceIf(var_dict[ap_2])
            elif ap_2 not in var_dict:
                Var_n = model.NewBoolVar(f"{var_n}")
                model.Add(Var_n == var_n).OnlyEnforceIf(var_dict[ap_1].Not())
                model.Add(Var_n == 0).OnlyEnforceIf(var_dict[ap_1])
            else:
                Var_n = model.NewBoolVar(f"{var_n}")
                model.Add(Var_n == var_n).OnlyEnforceIf([var_dict[ap_1].Not(), var_dict[ap_2].Not()])
                model.Add(Var_n == 0).OnlyEnforceIf(var_dict[ap_1])
                model.Add(Var_n == 0).OnlyEnforceIf(var_dict[ap_2])
            var_dict[var_n] = Var_n

        model.Add(sum(var_dict.values()) == value).OnlyEnforceIf(s)

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)
        if self.value_type == CONNECT:
            return self.create_constraints_connect(model, board, s)
        elif self.value_type == GROUP_4:
            return self.create_constraints_group_4(model, board, s)
        elif self.value_type == GROUP_3:
            return self.create_constraints_group_3(model, board, s)

        nei1_pos = [_pos for _pos in self.pos.neighbors(1, 1) if board.is_valid(_pos)]
        max_var = len([pos for pos, _ in board()])

        id_vars = {k: v for k, v in zip(nei1_pos, board.batch(nei1_pos, mode="var", special=ID_2A))}
        count_vars = {pos2seed(pos, board): board.get_variable(pos, special=COUNT_2A) for pos, _ in board()}

        sum_vars = {}
        for id_num, count_var in count_vars.items():
            nei1_count_var = model.new_int_var(0, count_var.domain.max(), "")
            eq_vars = []
            for nei1_id in id_vars.values():
                ueq_var = model.NewBoolVar(f'{self.pos}_{id_num}={nei1_id}')
                model.add(nei1_id == id_num).only_enforce_if(ueq_var.Not(), s)
                model.add(nei1_id != id_num).only_enforce_if(ueq_var, s)
                eq_vars.append(ueq_var)
                model.add(nei1_count_var == count_var).only_enforce_if(ueq_var.Not(), s)
            model.add(nei1_count_var == 0).only_enforce_if(eq_vars + [s])
            sum_vars[f"{self.pos}_sum_at_{id_num}"] = nei1_count_var

        if not sum_vars:
            raise ValueError("RS'传进来个棍木")

        cond_var = model.new_int_var(0, max_var, "")
        model.add(cond_var == sum(sum_vars.values()))
        if DEBUG:
            self.debug_vars[f"{self.pos}_result_var"] = cond_var
            self.debug_vars.update(sum_vars)
            self.debug_vars.update(id_vars)
        # else:
        model.add(sum(sum_vars.values()) == self.value.value).only_enforce_if(s)
