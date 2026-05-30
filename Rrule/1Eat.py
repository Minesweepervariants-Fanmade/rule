#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/05/20 00:32
# @Author  : Wu_RH
# @FileName: 1Eat.py
import math
from dataclasses import dataclass
from typing import Optional, Tuple, Set, Dict
from fractions import Fraction

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition, MASTER_BOARD
from minesweepervariants.impl.impl_obj import get_board
from minesweepervariants.impl.rule.Rrule import Quess
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.utils.image_create import get_dummy, get_text, get_col, get_row, get_image
from minesweepervariants.utils.impl_obj import MINES_TAG, VALUE_QUESS
from minesweepervariants.utils.tool import get_logger

BYTE_LENGTH = 3
CACHE: Dict['AbstractPosition', Dict[Fraction, Set[int]]] = {}
CACHE_CODE: Dict['AbstractPosition', Dict[int, Fraction]] = {}


def encode_int(num: int) -> bytes:
    """将整数编码为固定长度（BYTE_LENGTH）的字节串，不含 0xFF。小端序，高位补 0。"""
    if num < 0:
        raise ValueError("只支持非负整数")
    # 计算 255 进制表示（低位在前）
    digits = []
    temp = num
    while temp > 0:
        temp, r = divmod(temp, 255)
        digits.append(r)
    # 如果数字太大，超过固定长度则报错
    if len(digits) > BYTE_LENGTH:
        raise OverflowError(f"数字太大，需要至少 {len(digits)} 字节，当前 BYTE_LENGTH={BYTE_LENGTH}")
    # 补足到固定长度（末尾补 0，相当于高位补 0）
    digits += [0] * (BYTE_LENGTH - len(digits))
    return bytes(digits)   # 每个元素 0~254，不会出现 255


def decode_int(data: bytes) -> int:
    """将固定长度的字节串解码为整数。data 长度必须等于 BYTE_LENGTH。"""
    if len(data) != BYTE_LENGTH:
        raise ValueError(f"输入字节串长度必须为 {BYTE_LENGTH}，实际 {len(data)}")
    # 小端序：第 i 字节乘以 255^i
    num = 0
    for i, b in enumerate(data):
        if b > 254:
            raise ValueError(f"非法字节值 {b}（最大应为 254）")
        num += b * (255 ** i)
    return num


class GridPoint:
    x: Fraction
    y: Fraction

    def __init__(self, x: float | int | Fraction, y: float | int | Fraction):
        self.x = Fraction(x)
        self.y = Fraction(y)

    def __hash__(self):
        return hash((float(self.x), float(self.y)))

    def __eq__(self, other):
        if not isinstance(other, GridPoint):
            return False
        return self.x == other.x and self.y == other.y

    def __lt__(self, other):
        if not isinstance(other, GridPoint):
            return NotImplemented
        return (self.x, self.y) < (other.x, other.y)

    def __repr__(self):
        return f"({self.x},{self.y})"


@dataclass
class EdgePoint:
    point1: GridPoint
    point2: GridPoint

    def __init__(self, point1: GridPoint, point2: GridPoint):
        self.point1, self.point2 = point1, point2
        if self.point1 < self.point2:
            self.point1, self.point2 = self.point2, self.point1

    def __hash__(self):
        return hash(tuple(sorted([hash(self.point1), hash(self.point2)])))

    def __eq__(self, other):
        if not isinstance(other, EdgePoint):
            return False
        return self.point1 == other.point1 and self.point2 == other.point2

    def __repr__(self):
        return f"{self.point1}={self.point2}"

    def __contains__(self, item: GridPoint) -> bool:
        if not isinstance(item, GridPoint):
            return False
        # 水平线段：y 相同，x 在两端点之间
        if self.point1.y == self.point2.y:
            return item.y == self.point1.y and (
                    min(self.point1.x, self.point2.x) <= item.x <= max(self.point1.x, self.point2.x)
            )
        # 垂直线段：x 相同，y 在两端点之间
        elif self.point1.x == self.point2.x:
            return item.x == self.point1.x and (
                    min(self.point1.y, self.point2.y) <= item.y <= max(self.point1.y, self.point2.y)
            )
        # 理论上不应该走到这里（构造时就保证了水平或垂直）
        return False

    def __iter__(self):
        yield self.point1
        yield self.point2

    def on(self) -> Tuple[Fraction, bool]:
        """
        附着在Y上则返回True 附着在X上返回False
        """
        if self.point1.y == self.point2.y:
            return self.point1.y, True
        elif self.point1.x == self.point2.x:
            return self.point1.x, False
        else:
            raise ValueError("Edge未附着在平直线上")

    def length(self) -> Fraction:
        if self.point1.y == self.point2.y:
            return abs(self.point1.x - self.point2.x)
        elif self.point1.x == self.point2.x:
            return abs(self.point1.y - self.point2.y)
        else:
            raise ValueError("Edge未附着在平直线上")


def link_pos2gridPoint(
    board: "AbstractBoard",
    pos: 'AbstractPosition',
    point: GridPoint
) -> Optional[GridPoint]:
    # 连接两点并形成射线 检查他的落点 若落点范围在两点之间 则返回None 否则返回落点
    start_x = Fraction(pos.row) + Fraction(1, 2)
    start_y = Fraction(pos.col) + Fraction(1, 2)
    target_x = int(point.x)
    target_y = int(point.y)

    line_y_k = Fraction(target_x - start_x, target_y - start_y)
    line_y_b = start_x - line_y_k * start_y
    line_x_k = Fraction(target_y - start_y, target_x - start_x)
    line_x_b = start_y - line_x_k * start_x

    check_start_x = start_x
    check_end_x = int(start_x) + (1 if start_x < target_x else 0)

    check_y = start_y
    check_x = start_x

    while True:
        check_start_y = line_x_k * check_start_x + line_x_b
        check_end_y = line_x_k * check_end_x + line_x_b
        # print("range1", check_start_y, check_end_y, 1 if check_start_y < check_end_y else -1)
        if start_y > target_y:
            check_start_y = math.ceil(check_start_y) - 1
            check_end_y = math.floor(check_end_y) - 1
        else:
            check_start_y = math.floor(check_start_y)
            check_end_y = math.ceil(check_end_y)

        # print("range2", check_start_y, check_end_y, 1 if check_start_y < check_end_y else -1)

        if check_start_x < check_end_x:
            check_pos_x = int(check_start_x)
        else:
            check_pos_x = int(check_end_x)
        flag = False
        for check_pos_y in range(
            check_start_y, check_end_y,
            1 if check_start_y < check_end_y else -1
        ):
            if check_pos_y >= 0 and check_pos_x >= 0:
                check_pos = board.get_pos(check_pos_x, check_pos_y)
                # print("check_pos", check_pos, board.get_type(check_pos))
                if check_pos and board.get_type(check_pos) in "NC":
                    continue
            if check_pos_y == check_start_y:
                check_x = check_start_x
                check_y = line_x_k * check_start_x + line_x_b
            else:
                check_x = line_y_k * (check_pos_y + (check_start_y > check_end_y)) + line_y_b
                check_y = check_pos_y + (check_start_y > check_end_y)
            flag = True
            break

        if flag: break

        check_start_x = check_end_x
        check_end_x = check_end_x + (1 if start_x < target_x else -1)

    if min(float(start_y), target_y) < check_y < max(float(start_y), target_y):
        return None

    return GridPoint(check_x, check_y)


def _get_all_point(board: 'AbstractBoard', pos: 'AbstractPosition') -> Set[GridPoint]:
    checked = {pos}
    visited = set()

    visited_points = set()
    checked_points = set()  # 可以被连线的格点

    while checked:
        _checked = set()
        for check in checked:
            if check in visited_points:
                continue
            visited.add(check)
            # check的4个格点
            for dx, dy in ((0, 0), (0, 1), (1, 0), (1, 1)):
                point = GridPoint(check.row + dy, check.col + dx)
                if point in visited_points:
                    continue
                visited_points.add(point)

                # 检查该格点是否处于某个边界上 即四格是否右边界或雷
                if all(
                        point.y + dy >= 0 and point.x + dx >= 0
                        for dx, dy in ((0, 0), (0, -1), (-1, 0), (-1, -1))
                ):
                    check_positiones = [
                        board.get_pos(int(point.x + dx), int(point.y + dy))
                        for dx, dy in ((0, 0), (0, -1), (-1, 0), (-1, -1))
                    ]
                    if (
                            (None not in check_positiones) and
                            all(
                                (board.get_type(check_pos) in "NC")
                                for check_pos in check_positiones
                            )
                    ):
                        continue

                extension_point = link_pos2gridPoint(board, pos, point)
                if extension_point is None:
                    continue
                checked_points.add(point)
                if extension_point not in checked_points:
                    checked_points.add(extension_point)

            # check的上下左右pos
            for _check in check.neighbors(1, 1):
                if _check in visited:
                    continue
                if not board.is_valid(_check):
                    continue
                if board.get_type(_check) not in "NC":
                    continue
                _checked.add(_check)
        checked = _checked
    return checked_points


def _get_edges(board: 'AbstractBoard', checked_points: Set[GridPoint]) -> Set[EdgePoint]:
    edge_list = set()
    for point in checked_points:
        on_edge = []
        if (
                point.x != int(point.x) and
                point.y != int(point.y)
        ):
            raise ValueError("未落在格点或边上")
        if point.y != int(point.y):
            on_edge.append(EdgePoint(
                GridPoint(point.x, int(point.y)),
                GridPoint(point.x, int(point.y) + 1),
            ))
        elif point.x != int(point.x):
            on_edge.append(EdgePoint(
                GridPoint(int(point.x), point.y),
                GridPoint(int(point.x) + 1, point.y),
            ))
        else:
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                on_edge.append(EdgePoint(
                    point, GridPoint(point.x + dx, point.y + dy),
                ))
        for check_point in checked_points:
            if check_point == point:
                continue
            if not any(check_point in edge for edge in on_edge):
                continue
            if point.x == check_point.x:
                check_pos_a_y = check_pos_b_y = math.floor(min(
                    point.y, check_point.y
                ))
                check_pos_a_x = int(point.x)
                check_pos_b_x = int(point.x - 1)
            elif point.y == check_point.y:
                check_pos_a_x = check_pos_b_x = math.floor(min(
                    point.x, check_point.x
                ))
                check_pos_a_y = int(point.y)
                check_pos_b_y = int(point.y - 1)
            else:
                raise ValueError("该点未依附任何边")
            if not (
                    check_pos_a_x < 0 or
                    check_pos_a_y < 0 or
                    check_pos_b_x < 0 or
                    check_pos_b_y < 0
            ):
                check_pos_a = board.get_pos(check_pos_a_x, check_pos_a_y)
                check_pos_b = board.get_pos(check_pos_b_x, check_pos_b_y)
                if (
                        check_pos_a is not None and
                        check_pos_b is not None and
                        board.get_type(check_pos_a) in "NC" and
                        board.get_type(check_pos_b) in "NC"
                ):
                    continue
            edge_list.add(EdgePoint(
                point, check_point
            ))
    return edge_list


def _get_area(pos: 'AbstractPosition', edge_list: Set[EdgePoint]) -> Fraction:
    area = Fraction(0)
    for edge in edge_list:
        pos_value, is_y = edge.on()
        high = Fraction(abs(pos_value - (pos.col + 0.5 if is_y else pos.row + 0.5)))
        base = edge.length()
        area += high * base / 2

    return area


class Rule1Eat(AbstractClueRule):
    id = "1E@"
    name = "Eyesight@"
    name.zh_CN = "视野@"
    aliases = ("1Eat", "Eat")
    doc = "The clue indicates that the visible area outside of Ray (including itself) will be obstructed by Ray."
    doc.zh_CN = "线索表示能看到的非雷格面积（包括自身），雷会阻挡视线"
    tags = ["Untagged"]
    creation_time = "2026-04-30 00:21:47"
    author = ("NT", 2201963934)

    def __init__(self, board: AbstractBoard = None, data=None) -> None:
        super().__init__(board, data)
        self.all_integer = False
        if isinstance(data, str):
            if "!" in data:
                self.all_integer = True

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        for key in board.get_interactive_keys():
            for pos, _ in board("N", key=key):
                obj = self.get_obj(board, pos)
                board[pos] = obj
        return board

    def get_obj(self, board: 'AbstractBoard', pos: 'AbstractPosition') -> AbstractClueValue:
        logger = get_logger()
        checked_points = _get_all_point(board, pos)
        size = board.get_config(MASTER_BOARD, "size")[0]
        edge_list = _get_edges(board, checked_points)
        area = _get_area(pos, edge_list)
        logger.debug(f"area: {area}")
        logger.debug(f"geogebra[{pos}]: " + "{{" + ', '.join([
            f"({point.y}, {size - point.x})" for point in checked_points
        ]) + "}, {" + ', '.join([
            f"({pos.col + 0.5}, {size - pos.row - 0.5})" for pos, _ in board("F")
        ]) + "}, {" + ', '.join([
            f"Segment(({point_a.y}, {size - point_a.x}), ({point_b.y}, {size - point_b.x}))"
            for point_a, point_b in edge_list]
        ) + "}}")
        if self.all_integer:
            if area.denominator != 1:
                return Quess.ValueQuess(pos)
        return Value1Eat(pos, code=encode_int(area.numerator) + encode_int(area.denominator))


class Value1Eat(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        super().__init__(pos, code)
        self.numerator = decode_int(code[:BYTE_LENGTH])
        self.denominator = decode_int(code[BYTE_LENGTH:])

    def __repr__(self) -> str:
        return f"{Fraction(self.numerator, self.denominator)}"

    @classmethod
    def type(cls) -> bytes:
        return Rule1Eat.id.encode()

    def code(self) -> bytes:
        return encode_int(self.numerator) + encode_int(self.denominator)

    def compose(self, board):
        # 假分数转带分数
        whole = self.numerator // self.denominator
        rem = self.numerator % self.denominator

        # 纯整数
        if rem == 0:
            return get_col(
                get_dummy(height=0.175),
                get_text(str(whole)),
                get_dummy(height=0.175),
            )

        # 真分数部分：分子, 压扁的箭头, 分母 垂直排列
        num_str = str(rem)
        den_str = str(self.denominator)
        # 使用双向箭头并压扁 (width 拉长，height 很小)

        arrow = get_image(
            "double_horizontal_arrow",  # 假设 assets 中有 arrow_horizontal.png
            image_width=0.6,  # 水平拉长
            image_height=0.05,  # 竖直压扁
            dominant_by_height=False  # 宽度主导
        )

        fraction_col = get_col(
            get_text(num_str),
            arrow,
            get_text(den_str),
            spacing=0,
            dominant_by_height=False
        )

        # 整数部分为 0 则只显示分数
        if whole == 0:
            return fraction_col

        # 整数 + 分数水平并排
        return get_row(
            get_text(str(whole), width=0.3),
            fraction_col,
            spacing=-0.1,
            dominant_by_height=True
        )

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        # SUPER枚举大法
        global CACHE, CACHE_CODE

        def encode_board(_board: 'AbstractBoard', target_type: str):
            _int_code = 0
            for _, _obj_type in _board(mode="type"):
                _int_code <<= 1
                _int_code += _obj_type == target_type
            return _int_code

        def decode_board(_board_code: int, _board: 'AbstractBoard'):
            for pos, _ in list(_board())[::-1]:
                if _board_code & 1:
                    _board[pos] = MINES_TAG
                else:
                    _board[pos] = VALUE_QUESS
                _board_code >>= 1
            return _board

        def get_area(_board_code: int):
            _board = decode_board(_board_code, board_tmp.clone())
            checked_points = _get_all_point(_board, self.pos)
            edge_list = _get_edges(_board, checked_points)
            return _get_area(self.pos, edge_list)

        model = board.get_model()
        s = switch.get(model, self)

        master_board_code = encode_board(board, "F")
        mask_board_code = encode_board(board, "N")
        target_value = Fraction(self.numerator, self.denominator)
        board_tmp = get_board()(rules={}, size=board.get_config(MASTER_BOARD, "size"))

        if self.pos not in CACHE:
            CACHE[self.pos]: Dict[Fraction, Set[int]] = dict()
        if self.pos not in CACHE_CODE:
            CACHE_CODE[self.pos]: Dict[int, Fraction] = dict()

        sub = mask_board_code
        possible = set()
        get_logger().debug(f"{self.pos} possible start")
        while True:
            target_board_code = master_board_code | sub
            if target_board_code in CACHE_CODE[self.pos]:
                area = CACHE_CODE[self.pos][target_board_code]
            else:
                area = get_area(target_board_code)
                CACHE_CODE[self.pos][target_board_code] = area
                if area not in CACHE[self.pos]:
                    CACHE[self.pos][area] = set()
                CACHE[self.pos][area].add(target_board_code)
            if area == target_value:
                possible.add(target_board_code)
            if sub == 0:
                break
            sub = (sub - 1) & mask_board_code

        var_list = [var for _, var in board(mode="var")]
        get_logger().debug(f"{self.pos} possible legth: {len(possible)}")
        possible = [[(x >> i) & 1 == 1 for i in range(len(var_list))][::-1] for x in possible]
        get_logger().trace(f"{self.pos} var_list: {var_list}")
        get_logger().trace(f"{self.pos} possible: {possible}")
        model.add_allowed_assignments(
            var_list, possible
        ).OnlyEnforceIf(s)


def test1():
    from minesweepervariants.impl.board.version3.board import Board
    from minesweepervariants.impl.impl_obj import MINES_TAG
    import time
    import random
    board = Board(rules={}, size=(5, 5), code=None, default_special="raw")
    # root_pos = board.get_pos(0, 4)
    root_pos = board.get_pos(2, 4)
    # board[board.get_pos(0, 1)] = MINES_TAG
    # board[board.get_pos(0, 3)] = MINES_TAG
    # board[board.get_pos(1, 1)] = MINES_TAG
    # board[board.get_pos(1, 3)] = MINES_TAG
    # board[board.get_pos(2, 0)] = MINES_TAG
    # board[board.get_pos(2, 4)] = MINES_TAG
    # board[board.get_pos(3, 2)] = MINES_TAG
    # board[board.get_pos(3, 4)] = MINES_TAG
    # board[board.get_pos(4, 0)] = MINES_TAG
    # board[board.get_pos(4, 2)] = MINES_TAG
    time_sum = 0
    for _ in range(1000):
        positions = [pos for pos, _ in board()]
        positions = random.sample(positions, 10)
        _board = board.clone()
        for pos in positions:
            if pos == root_pos:
                continue
            _board[pos] = MINES_TAG
        # print(_board)
        rule = Rule1Eat()
        time_a = time.time()
        # rule.get_obj(board, root_pos)
        _get_all_point(_board, root_pos)
        used_time = time.time() - time_a
        print(f"used_time: {(used_time) * 1000:03f}ms")
        time_sum += used_time
    print(f"average time taken: {time_sum}ms")


def test2():
    from minesweepervariants.impl.board.version3.board import Board
    from minesweepervariants.impl.impl_obj import MINES_TAG
    board = Board(rules={}, size=(7, 7), code=None, default_special="raw")
    root_pos = board.get_pos(3, 3)
    board[board.get_pos(0, 2)] = MINES_TAG
    board[board.get_pos(0, 4)] = MINES_TAG
    board[board.get_pos(1, 3)] = MINES_TAG
    board[board.get_pos(2, 0)] = MINES_TAG
    board[board.get_pos(2, 6)] = MINES_TAG
    board[board.get_pos(3, 1)] = MINES_TAG
    board[board.get_pos(3, 5)] = MINES_TAG
    board[board.get_pos(4, 0)] = MINES_TAG
    board[board.get_pos(4, 6)] = MINES_TAG
    board[board.get_pos(5, 3)] = MINES_TAG
    board[board.get_pos(6, 2)] = MINES_TAG
    board[board.get_pos(6, 4)] = MINES_TAG
    print((4, 2), link_pos2gridPoint(board, root_pos, GridPoint(4, 2)))
    print((5, 3), link_pos2gridPoint(board, root_pos, GridPoint(5, 3)))
    print((5, 4), link_pos2gridPoint(board, root_pos, GridPoint(5, 4)))
    print((4, 5), link_pos2gridPoint(board, root_pos, GridPoint(4, 5)))
    print((3, 5), link_pos2gridPoint(board, root_pos, GridPoint(3, 5)))
    print((2, 4), link_pos2gridPoint(board, root_pos, GridPoint(2, 4)))
    print((2, 3), link_pos2gridPoint(board, root_pos, GridPoint(2, 3)))
    print((3, 2), link_pos2gridPoint(board, root_pos, GridPoint(3, 2)))


def test3():
    from minesweepervariants.impl.board.version3.board import Board
    from minesweepervariants.impl.impl_obj import MINES_TAG
    board = Board(rules={}, size=(5, 5), code=None, default_special="raw")
    root_pos = board.get_pos(0, 0)
    board[board.get_pos(4, 3)] = MINES_TAG
    board[board.get_pos(3, 1)] = MINES_TAG
    board[board.get_pos(3, 0)] = MINES_TAG
    grid_point = GridPoint(2, 2)
    print(board)
    print(link_pos2gridPoint(board, root_pos, grid_point))
    board[board.get_pos(4, 4)] = MINES_TAG
    print(board)
    print(link_pos2gridPoint(board, root_pos, grid_point))


def test4():
    def encode_board(_board: 'AbstractBoard'):
        if "N" in _board:
            return -1
        int_code = 0
        for pos, obj_type in board(mode="type"):
            int_code <<= 1
            int_code += obj_type == "F"
        return int_code

    def decode_board(_board_code: int, _board: 'AbstractBoard'):
        for pos, _ in list(_board())[::-1]:
            if _board_code & 1:
                _board[pos] = MINES_TAG
            else:
                _board[pos] = VALUE_QUESS
            _board_code >>= 1

    from minesweepervariants.impl.board.version3.board import Board
    import random

    board = Board(rules={}, size=(5, 5), code=None)
    board_tmp = board.clone()
    for pos, _ in board():
        board[pos] = MINES_TAG if random.random() < 0.5 else VALUE_QUESS
    print(board)
    board_code = encode_board(board)
    print(board_code)
    print(board_tmp)
    decode_board(board_code, board_tmp)
    print(board_tmp)


if __name__ == '__main__':
    test4()
