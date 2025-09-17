from abc import ABC, abstractmethod

from minesweepervariants.utils.tool import get_logger
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue


def eyesight_dfs(board: AbstractBoard, pos, value, move_funcs=None):
    if move_funcs is None:
        return []
    if not board.is_valid(pos):
        return []
    if value < 0:
        return
    move_func = move_funcs.pop()
    pos_t_list = []
    if not move_funcs:
        for i in range(1, value + 1):
            if (
                not board.is_valid(move_func(i)) or
                board.get_type(move_func(i)) == "F"
            ):
                return
            pos_t_list.append(move_func(i))
        else:
            yield from [[pos_t_list, [move_func(value + 1)]]]
        return
    if value == 0:
        for pos_list in eyesight_dfs(board, pos, value, move_funcs[:]):
            yield from [[pos_t_list + pos_list[0], [move_func(1)] + pos_list[1]]]
        return
    for i in range(value + 1):
        if i == 0:
            for pos_list in eyesight_dfs(board, pos, value - i, move_funcs[:]):
                yield pos_list[0] + pos_t_list[:], pos_list[1] + [move_func(i + 1)]
        elif (
            not board.is_valid(move_func(i)) or
            board.get_type(move_func(i)) == "F"
        ):
            for pos_list in eyesight_dfs(board, pos, value - i + 1, move_funcs[:]):
                yield pos_t_list[:] + pos_list[0], pos_list[1]
            return
        else:
            pos_t_list.append(move_func(i))
            for pos_list in eyesight_dfs(board, pos, value - i, move_funcs[:]):
                yield pos_list[0] + pos_t_list[:], pos_list[1] + [move_func(i + 1)]


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
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        self.value = code[0]
        self.pos = pos

    def __repr__(self):
        return str(self.value)
    
    @abstractmethod
    def direction_funcs(self):
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
        tmp_list = []

        for poses_t, poses_f in eyesight_dfs(
            board, self.pos, self.value - 1,
            self.direction_funcs()
        ):
            tmp = model.NewBoolVar("tmp")
            vars_t = board.batch(set(poses_t), "var")
            vars_f = board.batch(set(poses_f), "var")
            model.Add(sum(vars_t) == 0).OnlyEnforceIf(tmp)
            if vars_f and any(var is not None for var in vars_f):
                model.AddBoolAnd([var for var in vars_f if var is not None]).OnlyEnforceIf(tmp)
            tmp_list.append(tmp)
        get_logger().trace(f"[1E]: [{self.pos}]向model添加了{len(tmp_list)}种可能")
        model.AddBoolOr(tmp_list).OnlyEnforceIf(s)
