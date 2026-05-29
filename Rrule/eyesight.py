from abc import ABC, abstractmethod
from typing import List, Callable, Optional

from ortools.sat.python.cp_model import IntVar

from minesweepervariants.utils.tool import get_logger
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue


def eyesight_var(
    board: AbstractBoard, switch: IntVar,
    move_funcs: List[Callable[[int], Optional[AbstractPosition]]] = None
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
    def clue_type(cls):
        """
        需要返回线索对象类型
        """

    def fill(self, board: AbstractBoard):
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

            obj = self.clue_type()(pos, bytes([value]))
            board.set_value(pos, obj)
        return board


class AbstractEyesightClueValue(AbstractClueValue, ABC):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b'', *args, **kwargs):
        super().__init__(pos, *args, **kwargs)
        self.value = code[0]

    def __repr__(self):
        return str(self.value)

    @abstractmethod
    def direction_funcs(self) -> List[Callable[[int], AbstractPosition]]:
        """
        需要返回所有方向的函数
        """

    def code(self) -> bytes:
        return bytes([self.value])

    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        positions = []
        for direction_func in self.direction_funcs():
            n = 0
            while board.get_type(pos := direction_func(n)) not in "F":
                n += 1
                positions.append(pos)
        return positions

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        var_list = eyesight_var(
            board, s,
            self.direction_funcs()
        )
        # print(self.pos, var_list)
        model.add(sum(var_list) == self.value - 1).OnlyEnforceIf(s)
