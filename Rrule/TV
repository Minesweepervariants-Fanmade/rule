#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
[TV] Tapa View: 线索表示四方向上能看到的雷格数量，空格会阻挡视线
"""
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition


class RuleTV(AbstractClueRule):
    name = ["TV", "TapaView"]
    doc = "线索表示四方向上能看到的雷格数量，空格会阻挡视线"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        for pos, _ in board("N"):
            value = 0
            # 四方向的函数
            direction_funcs = [
                lambda _n: type(pos)(pos.x + _n, pos.y, pos.board_key),  # 右
                lambda _n: type(pos)(pos.x - _n, pos.y, pos.board_key),  # 左
                lambda _n: type(pos)(pos.x, pos.y + _n, pos.board_key),  # 上
                lambda _n: type(pos)(pos.x, pos.y - _n, pos.board_key)   # 下
            ]

            for fn in direction_funcs:
                n = 1
                while True:
                    next_pos = fn(n)
                    if not board.in_bounds(next_pos):
                        break
                    if board.get_type(next_pos) != "F":
                        break
                    value += 1
                    n += 1

            obj = ValueTV(pos, bytes([value]))
            board.set_value(pos, obj)
        return board


class ValueTV(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        self.value = code[0]
        self.pos = pos

    def __repr__(self):
        return str(self.value)

    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        positions = []
        for i in [
            (1, 0), (0, 1),
            (-1, 0), (0, -1),
        ]:
            n = 0
            while board.get_type(pos := self.pos.shift(i[0] * n, i[1] * n)) in "F":
                n += 1
                positions.append(pos)
        return positions

    @classmethod
    def type(cls) -> bytes:
        return RuleTV.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints(self, board: 'AbstractBoard', switch):
        def dfs(value: int, index=0, info: dict = None):
            if info is None:
                info = {"T": [], "F": []}

            if index == 4:
                if value == 0:
                    possible_list.append((set(info["T"]), [var for var in info["F"] if var is not None]))
                return

            pos = self.pos
            direction_funcs = [
                (lambda n: type(pos)(pos.x + n, pos.y, pos.board_key)),  # 右
                (lambda n: type(pos)(pos.x - n, pos.y, pos.board_key)),  # 左
                (lambda n: type(pos)(pos.x, pos.y + n, pos.board_key)),  # 上
                (lambda n: type(pos)(pos.x, pos.y - n, pos.board_key)),  # 下
            ]

            fn = direction_funcs[index]

            dfs(value, index + 1, info)

            for i in range(value):
                current_pos = fn(i + 1)
                if not board.in_bounds(current_pos):
                    dfs(value - i, index + 1, info)
                    break

                _var_t = board.get_variable(current_pos)
                if _var_t is None:
                    dfs(value - i, index + 1, info)
                    break

                next_pos = fn(i + 2)
                _var_f = board.get_variable(next_pos) if board.in_bounds(next_pos) else None

                info["T"].append(_var_t)
                info["F"].append(_var_f)
                dfs(value - (i + 1), index + 1, info)

                info["F"].pop(-1)
                info["T"].pop(-1)

        model = board.get_model()
        s = switch.get(model, self)
        possible_list = []

        dfs(value=self.value)
        tmp_list = []

        for vars_t, vars_f in possible_list:
            tmp = model.NewBoolVar("tmp")
            model.Add(sum(vars_t) == 0).OnlyEnforceIf(tmp)
            if vars_f and any(var is not None for var in vars_f):
                model.AddBoolAnd([var for var in vars_f if var is not None]).OnlyEnforceIf(tmp)
            tmp_list.append(tmp)

        if tmp_list:
            model.AddBoolOr(tmp_list).OnlyEnforceIf(s)
