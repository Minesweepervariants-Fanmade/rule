#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/04 07:39
# @Author  : Wu_RH
# @FileName: 4V.py
"""
[4V']2X'plusplus: 线索表示数字是三个题板中相同位置的其中某两个范围中心3*3区域的雷总数
"""
from typing import Dict

from minesweepervariants.utils.web_template import MultiNumber
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition, MASTER_BOARD
from ....utils.image_create import get_text, get_row
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG
from ....utils.tool import get_random

NAME_4Vp = ["4Va", "4Vb"]


class Rule4Vp(AbstractClueRule):
    name = ["4V'", "映射'"]
    doc = "线索表示数字是三个题板中相同位置的其中某两个范围中心3*3区域的雷总数"

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        size = (board.boundary().x + 1, board.boundary().y + 1)
        board.generate_board(NAME_4Vp[0], size)
        board.generate_board(NAME_4Vp[1], size)
        board.set_config(NAME_4Vp[0], "interactive", True)
        board.set_config(NAME_4Vp[1], "interactive", True)
        board.set_config(NAME_4Vp[0], "row_col", True)
        board.set_config(NAME_4Vp[1], "row_col", True)
        board.set_config(NAME_4Vp[0], "VALUE", VALUE_QUESS)
        board.set_config(NAME_4Vp[1], "VALUE", VALUE_QUESS)
        board.set_config(NAME_4Vp[0], "MINES", MINES_TAG)
        board.set_config(NAME_4Vp[1], "MINES", MINES_TAG)

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        random = get_random()

        for key in [MASTER_BOARD] + NAME_4Vp:
            for pos, _ in board("N", key=key):
                neighbors_list = []
                for _key in [MASTER_BOARD] + NAME_4Vp:
                    _pos = pos.clone()
                    _pos.board_key = _key
                    neighbors_list.append(_pos.neighbors(0, 2))
                value_a, value_b = random.sample([board.batch(positions, mode="type").count("F")
                                                  for positions in neighbors_list], 2)
                value = Value4Vp(pos=pos, code=bytes([value_b << 4 | value_a]))
                board.set_value(pos, value)

        return board


class Value4Vp(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        self.neighbors_list = []
        for key in [MASTER_BOARD] + NAME_4Vp:
            _pos = pos.clone()
            _pos.board_key = key
            self.neighbors_list.append(_pos.neighbors(0, 2))
        self.value_a = code[0] & 0xf
        self.value_b = code[0] >> 4
        self.pos = pos

    @classmethod
    def method_choose(cls) -> int:
        return 1

    @classmethod
    def type(cls) -> bytes:
        return Rule4Vp.name[0].encode("ascii")

    def __repr__(self) -> str:
        value = [self.value_a, self.value_b]
        value.sort()
        return f"{value[0]} {value[1]}"

    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        return (self.neighbors_list[0] +
                self.neighbors_list[1] +
                self.neighbors_list[2])

    def web_component(self, board) -> Dict:
        value = [self.value_a, self.value_b]
        value.sort()
        return MultiNumber(value)

    def compose(self, board) -> Dict:
        value = [self.value_a, self.value_b]
        value.sort()
        text_a = get_text(str(value[0]))
        text_b = get_text(str(value[1]))
        return get_row(
            text_a,
            text_b
        )

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        # 收集三组邻居的有效位置
        groups = []
        for i, neighbor in enumerate(self.neighbors_list):
            var_list = board.batch(neighbor, mode="variable", drop_none=True)
            if var_list:
                groups.append({
                    "index": i,
                    "vars": var_list,
                    "sum": sum(var_list)
                })

        num_groups = len(groups)

        # 如果有效组少于2个，无法满足要求（添加不可能约束）
        if num_groups < 2:
            model.AddBoolOr([])
            return

        # 创建选择变量：选择哪两组分别对应值A和值B
        a_group = model.NewIntVar(0, num_groups - 1, f"[{Rule4Vp.name}]a_group")
        b_group = model.NewIntVar(0, num_groups - 1, f"[{Rule4Vp.name}]b_group")

        # 确保选择的组不同
        model.Add(a_group != b_group).OnlyEnforceIf(s)

        # 为每个组创建指示变量
        group_flags = []
        for i, group in enumerate(groups):
            # 创建指示变量：当前组是否被选为值A的组
            is_a_group = model.NewBoolVar(f"is_a_group_{i}")
            model.Add(a_group == i).OnlyEnforceIf([is_a_group, s])
            model.Add(a_group != i).OnlyEnforceIf([is_a_group.Not(), s])

            # 创建指示变量：当前组是否被选为值B的组
            is_b_group = model.NewBoolVar(f"is_b_group_{i}")
            model.Add(b_group == i).OnlyEnforceIf([is_b_group, s])
            model.Add(b_group != i).OnlyEnforceIf([is_b_group.Not(), s])

            # 添加约束：如果被选为值A的组，则必须等于值A
            model.Add(group["sum"] == self.value_a).OnlyEnforceIf([is_a_group, s])

            # 添加约束：如果被选为值B的组，则必须等于值B
            model.Add(group["sum"] == self.value_b).OnlyEnforceIf([is_b_group, s])

            group_flags.append((is_a_group, is_b_group))

        # 确保恰好一组被选为值A，一组被选为值B
        model.Add(sum([a for a, _ in group_flags]) == 1).OnlyEnforceIf(s)
        model.Add(sum([b for _, b in group_flags]) == 1).OnlyEnforceIf(s)

        # 第三组没有约束（可以任意值）

    def code(self) -> bytes:
        return bytes([self.value_b << 4 | self.value_a])
