#!/usr/bin/env python3
"""
[3N] 范数 (Norm)：线索(a_p)表示距离自己lp范数最近的雷的lp范数大小为a。(p=0,1,2,00)
"""
from typing import Dict, Literal

from ....abs.Rrule import AbstractClueValue, AbstractClueRule
from ....abs.board import AbstractPosition, AbstractBoard
from ....utils.image_create import get_text, get_image, get_row, get_col, get_dummy
from ....utils.tool import get_random

P = Literal[0, 1, 2] | Literal['00']
Root = tuple[int, int]


def simplify_sqrt(n):
    c = 1
    i = 2
    while i * i <= n:
        while n % (i * i) == 0:
            c *= i
            n //= i * i
        i += 1
    return c, n


def norm(dx, dy, p: P) -> Root:
    """
    计算点(dx, dy)在lp范数下的距离

    参数:
        dx: x方向的距离
        dy: y方向的距离
        p: lp范数的阶数

    返回:
        点(dx, dy)在lp范数下的距离
    """
    if p == 0:
        return 2 if dx != 0 and dy != 0 else 1, 1
    elif p == 1:
        return abs(dx) + abs(dy), 1
    elif p == 2:
        r2 = dx ** 2 + dy ** 2
        if int(r2 ** 0.5) ** 2 == r2:
            return int(r2 ** 0.5), 1
        else:
            return r2, 2
    elif p == '00':
        return max(abs(dx), abs(dy)), 1
    else:
        raise ValueError(f"Unsupported norm type: {p}")


def format(n: Root, p: P):
    """
    格式化输出范数的字符串表示
    """
    if n[1] == 1:
        return f'{n[0]}_{p}'
    elif n[1] == 2:
        c, n_ = simplify_sqrt(n[0])
        return f"{c if c > 1 else ''}√{n_}" if n_ > 1 else str(c) + f'_{p}'
    else:
        raise ValueError(f"Unsupported root type: {n[1]}")


class BaseRule3N(AbstractClueRule):
    name = ["3N", "范数", "Norm"]
    doc = "线索(a_p)表示距离自己lp范数最近的雷的lp范数大小为a。(p=0,1,2,00)"
    p: P = -1

    def __init__(self, board: AbstractBoard, data: list[AbstractClueRule] = None):
        super().__init__(None, None)
        for key in board.get_interactive_keys():
            board.set_config(key, "by_mini", True)

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        boards = []
        for rule in [Rule3N0(board), Rule3N1(board),
                     Rule3N2(board), Rule3NInf(board)]:
            boards.append(rule._fill(board.clone()))
        for key in board.get_board_keys():
            for pos, _ in board("N", key=key):
                values = [_board.get_value(pos)
                          for _board in boards
                          if _board.get_type(pos) != "N"]
                if not values:
                    continue
                board.set_value(pos, get_random().choice(values))
        return board

    #
    def _fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        if len([_ for _ in board("F")]) < 1:
            return board

        for pos, _ in board("N"):
            p: P = self.p
            min_norm = None

            # 遍历所有雷的位置
            for mine_pos, _ in board("F"):
                dx = mine_pos.x - pos.x
                dy = mine_pos.y - pos.y
                mine_norm = norm(dx, dy, p)

                if min_norm is None or (mine_norm[0] < min_norm[0] or
                                        (mine_norm[0] == min_norm[0] and mine_norm[1] < min_norm[1])):
                    min_norm = mine_norm

            if min_norm is not None:
                # 编码范数值和p值
                if p == '00':
                    p_val = 100
                else:
                    p_val = int(p)
                obj = self.clue_class()(pos, bytes([min_norm[0], min_norm[1], p_val]))
                board.set_value(pos, obj)

        return board

    def clue_class(self):
        return getattr(self, 'clue', BaseValue3N)


class BaseValue3N(AbstractClueValue):
    name = "3N"

    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        self.pos = pos
        if len(code) >= 3:
            self.n = (code[0], code[1])  # (数值, 根次数)
            if code[2] == 100:
                self.p: P = '00'
            elif code[2] == 0:
                self.p: P = 0
            elif code[2] == 1:
                self.p: P = 1
            elif code[2] == 2:
                self.p: P = 2
            else:
                self.p: P = 2  # 默认值
        else:
            self.n = (1, 1)
            self.p: P = 2

    def __repr__(self):
        return format(self.n, self.p)

    def web_component(self, board) -> Dict:
        if self.n[1] == 1:
            return get_text(str(self.n[0]))
        elif self.n[1] == 2:
            value_a, value_b = simplify_sqrt(self.n[0])
            if value_b == -1:
                return get_text(str(value_a))
            if value_a == -1:
                return get_text(
                    "$\\sqrt{" + str(value_b) + "}$"
                )
            else:
                return get_text(
                    "$" + str(value_a) +
                    "\\sqrt{" + str(value_b) +
                    "}$"
                )
        else:
            raise ValueError("Unsupported root type")

    def compose(self, board) -> Dict:
        if self.n[1] == 1:
            return get_col(
                get_dummy(height=0.175),
                get_text(str(self.n[0])),
                get_dummy(height=0.175),
            )
        elif self.n[1] == 2:
            value_a, value_b = simplify_sqrt(self.n[0])
            if value_a == 1:
                return get_row(
                    get_image("sqrt"),
                    get_text(str(value_b)),
                    spacing=-0.15
                )
            else:
                return get_row(
                    get_text(str(value_a)),
                    get_image("sqrt"),
                    get_text(str(value_b)),
                    spacing=-0.2
                )
        else:
            raise ValueError("Unsupported root type")

    @classmethod
    def type(cls) -> bytes:
        return cls.name.encode('ascii')

    def code(self) -> bytes:
        if self.p == '00':
            p_val = 100
        else:
            p_val = int(self.p)
        return bytes([self.n[0], self.n[1], p_val])

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        # 为当前线索位置创建约束
        # 确保存在一个雷，其lp范数等于线索值
        constraint_vars = []

        for mine_pos, mine_var in board(mode="variable"):
            if board.get_type(mine_pos) in ["N", "F"]:  # 可能的雷位置
                dx = mine_pos.x - self.pos.x
                dy = mine_pos.y - self.pos.y

                # 计算这个位置到线索位置的lp范数
                pos_norm = norm(dx, dy, self.p)

                # 如果范数匹配，则这个位置可能是最近的雷
                if pos_norm == self.n:
                    # 创建一个布尔变量表示这个雷是最近的
                    is_closest = model.NewBoolVar(f"[3N]_{self.pos}_{mine_pos}")
                    model.Add(mine_var == 1).OnlyEnforceIf([is_closest, s])

                    # 确保没有更近的雷
                    for other_pos, other_var in board(mode="variable"):
                        if other_pos != mine_pos and board.get_type(other_pos) in ["N", "F"]:
                            other_dx = other_pos.x - self.pos.x
                            other_dy = other_pos.y - self.pos.y
                            other_norm = norm(other_dx, other_dy, self.p)

                            # 如果有更近的雷，则当前雷不能是最近的
                            if (other_norm[0] < pos_norm[0] or
                                    (other_norm[0] == pos_norm[0] and other_norm[1] < pos_norm[1])):
                                model.Add(other_var == 0).OnlyEnforceIf([is_closest, s])

                    constraint_vars.append(is_closest)

        # 至少有一个雷满足条件
        if constraint_vars:
            model.AddBoolOr(constraint_vars).OnlyEnforceIf(s)


class Value3N0(BaseValue3N):
    name = "3N0"
    p = 0


class Rule3N0(BaseRule3N):
    name = "3N0"
    p = 0
    clue = Value3N0


class Value3N1(BaseValue3N):
    name = "3N1"
    p = 1


class Rule3N1(BaseRule3N):
    name = "3N1"
    p = 1
    clue = Value3N1


class Value3N2(BaseValue3N):
    name = "3N2"
    p = 2


class Rule3N2(BaseRule3N):
    name = "3N2"
    p = 2
    clue = Value3N2


class Value3NInf(BaseValue3N):
    name = "3N00"
    p = '00'


class Rule3NInf(BaseRule3N):
    name = "3N00"
    p = '00'
    clue = Value3NInf
