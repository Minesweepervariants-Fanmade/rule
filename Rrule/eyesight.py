from abc import ABC, abstractmethod
from typing import List, Callable, Optional, cast, Type

from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap

from minesweepervariants.board import Board, Position, JSONObject
from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template, Template


def eyesight_var(
    board: Board, switch: IntVar,
    move_funcs: List[Callable[[int], Optional[Position]]] = None
) -> List[IntVar]:
    if move_funcs is None:
        move_funcs = []
    result_vars = []
    model = board.get_model()
    for move_func in move_funcs:
        tmp_vars = []
        index = 1
        while board.is_valid(_pos := move_func(index)):
            tmp_vars.append(_pos)
            index += 1
        if not tmp_vars:
            continue
        tmp_var = model.new_int_var(0, index, "")
        result_vars.append(tmp_var)
        pos_vars = board.batch(tmp_vars, "var")
        for index in range(len(tmp_vars)):
            false_var = [var.Not() for var in pos_vars[:index]]
            true_var = pos_vars[index]
            tmp_bool = model.new_bool_var("")
            model.add(tmp_var == index).OnlyEnforceIf(tmp_bool)
            model.add(tmp_var != index).OnlyEnforceIf(tmp_bool.Not())
            if false_var:
                model.add_bool_and(false_var).OnlyEnforceIf(tmp_bool, switch)
            model.add_bool_and(true_var).OnlyEnforceIf(tmp_bool, switch)
    return result_vars


class AbstractEyesightClueRule(AbstractClueRule, ABC):
    @staticmethod
    @abstractmethod
    def direction_funcs(pos):
        """
        需要返回所有方向的函数
        """

    @classmethod
    @abstractmethod
    def clue_type(cls) -> Type['AbstractEyesightClueValue']:
        """
        需要返回线索对象类型
        """

    def fill(self, board: Board):
        for pos, _ in board("N"):
            value = 1  # 包括自身
            # 四个斜向方向的函数
            direction_funcs = self.direction_funcs(pos)

            for fn in direction_funcs:
                n = 1
                while True:
                    next_pos = fn(n)
                    if not board.in_bounds(next_pos):
                        break
                    if board.get_type(next_pos) == "F":  # 遇到雷，视线被阻挡
                        break
                    value += 1
                    n += 1

            obj = self.clue_type()(pos, value)
            board.set_value(pos, obj)
        return board


class AbstractEyesightClueValue(AbstractClueValue, ABC):
    def __init__(self, pos: 'Position', value: int, *args: object, **kwargs: object):
        super().__init__(pos, value, *args, **kwargs)
        self.value: SingleIntValue = SingleIntValue(value)
        self.pos = pos

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)

        if not is_value_template(_data):
            raise TypeError("value is not template")

        template_data = cast(Template, _data)
        value = SingleIntValue.try_from(template_data)

        if value is None:
            raise ValueError("value is empty")

        return cls(pos, value.value)

    @abstractmethod
    def direction_funcs(self) -> List[Callable[[int], Position]]:
        """
        需要返回所有方向的函数
        """

    def high_light(self, board: 'Board') -> list['Position']:
        positions = []
        for direction_func in self.direction_funcs():
            n = 0
            while board.get_type(pos := direction_func(n)) not in "F":
                n += 1
                positions.append(pos)
        return positions

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)

        var_list = eyesight_var(
            board, s,
            self.direction_funcs()
        )
        # print(self.pos, var_list)
        model.add(sum(var_list) == self.value.value - 1).OnlyEnforceIf(s)
