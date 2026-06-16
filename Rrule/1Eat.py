#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/05/20 00:32
# @Author  : Wu_RH
# @FileName: 1Eat.py
import itertools
import math
from typing import Optional, Tuple, Set, List, Mapping, Union, Callable
from fractions import Fraction

from ortools.sat.python.cp_model import CpModel, IntVar

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position, MASTER_BOARD_KEY
from minesweepervariants.immutable_dict import ImmutableDict
from minesweepervariants.json_object import JSONObject
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.utils.image_template import get_dummy, get_text, get_col, get_row, get_image
from minesweepervariants.utils.impl_obj import VALUE_QUESS, MINES_TAG
from minesweepervariants.utils.tool import get_logger

EXPONENT = 15
ALLOW_ERROR = 0


class GridPoint:
    """
    精确的坐标点
    """
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

    def __iter__(self):
        yield self.x
        yield self.y

    def __repr__(self):
        return f"({self.x},{self.y})"


class EdgePoint:
    """
    两坐标点连成的边
    """
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
        return f"Segment({self.point1},{self.point2})"

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
        raise ValueError("Edge未附着在平直线上")

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

    def intersection(self, other: 'EdgePoint') -> Union[GridPoint, 'EdgePoint', None]:
        """计算两条水平/垂直线段的交点"""
        if not isinstance(other, EdgePoint):
            return NotImplemented

        # 判断自身与对方的朝向
        self_horiz = self.point1.y == self.point2.y
        other_horiz = other.point1.y == other.point2.y

        # 1) 两条水平线段
        if self_horiz and other_horiz:
            if self.point1.y != other.point1.y:
                return None
            y = self.point1.y
            sx1, sx2 = self.point1.x, self.point2.x
            ox1, ox2 = other.point1.x, other.point2.x
            lo = max(min(sx1, sx2), min(ox1, ox2))
            hi = min(max(sx1, sx2), max(ox1, ox2))
            if lo > hi:
                return None
            if lo == hi:
                return GridPoint(lo, y)
            return EdgePoint(GridPoint(lo, y), GridPoint(hi, y))

        # 2) 两条垂直线段
        if not self_horiz and not other_horiz:
            if self.point1.x != other.point1.x:
                return None
            x = self.point1.x
            sy1, sy2 = self.point1.y, self.point2.y
            oy1, oy2 = other.point1.y, other.point2.y
            lo = max(min(sy1, sy2), min(oy1, oy2))
            hi = min(max(sy1, sy2), max(oy1, oy2))
            if lo > hi:
                return None
            if lo == hi:
                return GridPoint(x, lo)
            return EdgePoint(GridPoint(x, lo), GridPoint(x, hi))

        # 3) 一水平一垂直
        # 统一为 self 水平，other 垂直
        if not self_horiz and other_horiz:
            return other.intersection(self)

        # self 水平，other 垂直
        hy = self.point1.y
        hx_min = min(self.point1.x, self.point2.x)
        hx_max = max(self.point1.x, self.point2.x)

        vx = other.point1.x
        vy_min = min(other.point1.y, other.point2.y)
        vy_max = max(other.point1.y, other.point2.y)

        if hx_min <= vx <= hx_max and vy_min <= hy <= vy_max:
            return GridPoint(vx, hy)
        return None

    def adjacent_cells[T](self, get_pos: Callable[[int, int], T]) -> Tuple[T, T]:
        """返回水平/垂直单位边所夹的两个格子中心点"""
        # p1, p2 = self.point1, self.point2

        if self.point1.y == self.point2.y:  # 水平边
            y = self.point1.y
            x_min = min(self.point1.x, self.point2.x)
            bottom = get_pos(int(x_min), int(y - 1))
            top = get_pos(int(x_min), int(y))
            return bottom, top

        if self.point1.x == self.point2.x:  # 垂直边
            x = self.point1.x
            y_min = min(self.point1.y, self.point2.y)
            left = get_pos(int(x - 1), int(y_min))
            right = get_pos(int(x), int(y_min))
            return left, right

        raise ValueError("Edge must be horizontal or vertical")


def link_pos2gridPoint(
    board: "Board",
    pos: 'Position',
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


def _get_all_point(board: 'Board', pos: 'Position') -> Set[GridPoint]:
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


def _get_edges(board: 'Board', checked_points: Set[GridPoint]) -> Set[EdgePoint]:
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


def _get_area(pos: 'Position', edge_list: Set[EdgePoint]) -> List[Fraction]:
    area = []
    for edge in edge_list:
        pos_value, is_y = edge.on()
        high = Fraction(abs(pos_value - (pos.col + 0.5 if is_y else pos.row + 0.5)))
        base = edge.length()
        area.append(high * base / 2)

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

    def __init__(self, board: Board = None, data=None) -> None:
        super().__init__(board, data)
        self.all_integer = False
        if isinstance(data, str):
            if "!" in data:
                self.all_integer = True

    def fill(self, board: 'Board') -> 'Board':
        for key in board.get_interactive_keys():
            for pos, _ in board("N", key=key):
                obj = self.get_obj(board, pos)
                board[pos] = obj
        return board

    def get_obj(self, board: 'Board', pos: 'Position') -> AbstractClueValue:
        logger = get_logger()
        checked_points = _get_all_point(board, pos)
        size = board.get_config(MASTER_BOARD_KEY, "size")[0]
        edge_list = _get_edges(board, checked_points)
        area_list = _get_area(pos, edge_list)
        approx_area = sum([int((1 << EXPONENT) * area) for area in area_list])
        area_sum = sum(area_list)
        logger.debug(
            f"area: {area_sum}({float(area_sum)}), "
            f"approx_area: {approx_area / (2 ** EXPONENT)}, "
            f"devia: {approx_area / (2 ** EXPONENT) - area_sum}"
        )
        logger.debug(f"geogebra[{pos}]: " + "{{" + ', '.join([
            f"({point.y}, {size - point.x})" for point in checked_points
        ]) + "}, {" + ', '.join([
            f"({pos.col + 0.5}, {size - pos.row - 0.5})" for pos, _ in board("F")
        ]) + "}, {" + ', '.join([
            f"Segment(({point_a.y}, {size - point_a.x}), ({point_b.y}, {size - point_b.x}))"
            for point_a, point_b in edge_list]
        ) + "}}")

        if self.all_integer:
            if area_sum.denominator != 1:
                return VALUE_QUESS
        return Value1Eat(
            pos, numerator=area_sum.numerator,
            denominator=area_sum.denominator,
            appro_area=approx_area,
            exponent=EXPONENT,
        )


class Value1Eat(AbstractClueValue):
    id = Rule1Eat.id
    def __init__(
        self, pos: 'Position',
        numerator: int,
        denominator: int,
        appro_area: int,
        exponent: int,
    ):
        super().__init__(pos)
        self.numerator = numerator
        self.denominator = denominator
        self.appro_area = appro_area
        self.exponent = exponent

    @classmethod
    def type(cls) -> bytes:
        return Rule1Eat.id.encode()

    def __repr__(self) -> str:
        return f"{Fraction(self.numerator, self.denominator)}"

    def web_component(self, board: 'AbstractBoard') -> Mapping[str, object]:
        whole = self.numerator // self.denominator
        rem = self.numerator % self.denominator
        # if rem == 0:
        #     return get_text(str(whole))
        #
        # if whole == 0:
        #     # 真分数或假分数（无整数部分）
        #     latex_str = f"\\frac{{{self.numerator}}}{{{self.denominator}}}"
        # else:
        #     # 带分数：整数部分 + 真分数
        #     latex_str = f"{whole}\\frac{{{rem}}}{{{self.denominator}}}"
        #
        # return get_text(latex_str)

        # 能整除 → 直接返回整数
        if rem == 0:
            return get_text(str(whole))

        num_str = str(rem)
        den_str = str(self.denominator)

        # 构建分数部分：分子、横线、分母 垂直排列
        # 横线使用 "—"（更长且细）或 "---"，并强制设置高度为 4px（或极小值）
        fraction_col = get_col(
            get_text(num_str),
            get_text("---"),  # 横线压扁：高度4px，字体大小不影响高度
            get_text(den_str),
        )

        # 无整数部分 → 直接返回分数
        if whole == 0:
            return fraction_col

        # 带分数：整数 + 分数 左右排列
        return get_row(
            get_col(get_text(str(whole))),  # 整数部分宽度占比 0.3，避免被挤压
            fraction_col,
        )

    def high_light(self, board: 'AbstractBoard') -> List['AbstractPosition'] | None:
        high_lights = set()
        all_point = _get_all_point(board, self.pos)
        all_edge = _get_edges(board, all_point)

        for edge in all_edge:
            p1, p2 = edge.adjacent_cells(lambda row, col: (
                board.get_pos(row, col, self.pos.board_key)
                if (
                    0 <= row <= board.boundary(self.pos.board_key).row and
                    0 <= col <= board.boundary(self.pos.board_key).col
                ) else None
            ))
            if p1 is None or board.get_type(p1) == "F":
                high_lights.add(p2)
            if p2 is None or board.get_type(p2) == "F":
                high_lights.add(p1)

        checked_poses = [self.pos]
        visible_poses = []
        while checked_poses:
            wait_check = []
            for checked_pos in checked_poses:
                if checked_pos in visible_poses:
                    continue
                visible_poses.append(checked_pos)
                if board.get_type(checked_pos) in "F":
                    continue
                flag = 0
                if checked_pos in high_lights:
                    flag = 2
                for dx, dy in [(0, 0), (0, 1), (1, 0), (1, 1)]:
                    if flag > 1:
                        break
                    point = GridPoint(checked_pos.row + dx, checked_pos.col + dy)
                    if not link_pos2gridPoint(board, self.pos, point):
                        continue
                    flag += 1
                if flag > 1:
                    wait_check.extend(checked_pos.neighbors(1))
                    high_lights.add(checked_pos)
            checked_poses = wait_check

        return list(high_lights)

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

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        return cls(pos, data["numerator"], data["denominator"], data["appro_area"], data["exponent"])

    def json(self) -> 'JSONObject':
        return ImmutableDict({
            "numerator": self.numerator, "denominator": self.denominator,
            "appro_area": self.appro_area, "exponent": self.exponent
        })

    def create_constraints(self, board: 'Board', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)
        intvar_list: List[IntVar] = []
        start_point = GridPoint(self.pos.row + Fraction(1, 2), self.pos.col + Fraction(1, 2))
        board_tmp = board.__class__()
        for board_key in board.get_interactive_keys():
            board_tmp.generate_board(board_key , size=board.get_config(board_key, "size"))
        for pos_row, pos_col in itertools.product(
            range(0, board.boundary(self.pos.board_key).row + 2),
            range(0, board.boundary(self.pos.board_key).col + 2)
        ):
            root_point = GridPoint(pos_row, pos_col)
            if pos_col < board.boundary(self.pos.board_key).col + 1:
                edge_r = EdgePoint(root_point, GridPoint(pos_row, pos_col + 1))
                intvar_list.append(self._get_edge_area(board, start_point, model, edge_r, board_tmp))
            if pos_row < board.boundary(self.pos.board_key).row + 1:
                edge_d = EdgePoint(root_point, GridPoint(pos_row + 1, pos_col))
                intvar_list.append(self._get_edge_area(board, start_point, model, edge_d, board_tmp))

        intvar_sum = sum(intvar_list)

        if ALLOW_ERROR > 0:
            get_logger().trace(f"[{self.pos}] sum.ub = {sum([intvar.domain.max() for intvar in intvar_list])}")
            get_logger().trace(f"[{self.pos}]({self.numerator}/{self.denominator}) appro_area = {self.appro_area}")
            get_logger().trace(f"[{self.pos}] sum ~ {self.appro_area} ± {ALLOW_ERROR}")
            # 允许误差范围：appro_area - allow_error <= intvar_sum <= appro_area + allow_error
            lower_bound = self.appro_area - ALLOW_ERROR
            upper_bound = self.appro_area + ALLOW_ERROR

            model.add(intvar_sum >= lower_bound).OnlyEnforceIf(s)
            model.add(intvar_sum <= upper_bound).OnlyEnforceIf(s)
        if ALLOW_ERROR == 0:
            get_logger().trace(f"[{self.pos}] sum.ub = {sum([intvar.domain.max() for intvar in intvar_list])}")
            get_logger().trace(f"[{self.pos}]({self.numerator}/{self.denominator}) appro_area = {self.appro_area}")
            model.add(intvar_sum == self.appro_area).OnlyEnforceIf(s)

    def _get_edge_area(
        self, board: 'Board', point: 'GridPoint',
        model: CpModel, edge: 'EdgePoint', board_tmp: 'Board'
    ) -> IntVar:
        ub = 1 << (self.exponent - 1)
        pos_value, is_y = edge.on()
        hight = Fraction(abs(pos_value - (self.pos.col + 0.5 if is_y else self.pos.row + 0.5)))
        result_var = model.new_int_var(0, int(ub * hight), f"{edge}->{self.pos}")

        positions_list, on_flag = self._get_edge_range(board, edge, point)
        get_logger().trace(f"{self.pos}, {positions_list}")

        kill_map: List[Position] = []

        if len(positions_list) == 0:
            raise ValueError("empty positions")
        for positions in positions_list:
            if None in positions:
                raise ValueError("None in positions")
            if len(positions) == 0:
                raise ValueError("empty positions")
            if len(positions) == 1:
                position = positions[0]
                kill_map.append(position)
                positions.clear()
                continue
        if len(positions_list) == 1:
            for pos in positions_list[0]:
                kill_map.append(pos)
            positions_list[0].clear()

        remap_pos = {}
        positions = set([j for i in positions_list for j in i])
        if is_y:
            if int(edge.point2.y) < on_flag:
                edge_on_pos = None
            else:
                edge_on_pos = board_tmp.get_pos(int(edge.point2.x), int(edge.point2.y) - on_flag)
        else:
            if int(edge.point2.x) < on_flag:
                edge_on_pos = None
            else:
                edge_on_pos = board_tmp.get_pos(int(edge.point2.x) - on_flag, int(edge.point2.y))

        if edge_on_pos is not None:
            board_tmp[edge_on_pos] = MINES_TAG

        for pos in positions:
            if edge_on_pos is not None:
                if pos in edge_on_pos.neighbors(1):
                    kill_map.append(pos)
                    board_tmp[pos] = None
                    continue
            if pos == board_tmp.get_pos(int(edge.point2.x), int(edge.point2.y)):
                kill_map.append(pos)
                board_tmp[pos] = None
                continue
            if pos == self.pos:
                kill_map.append(pos)
                board_tmp[pos] = None
                continue
            board_tmp[pos] = MINES_TAG
            point1 = link_pos2gridPoint(board_tmp, self.pos, edge.point1)
            point2 = link_pos2gridPoint(board_tmp, self.pos, edge.point2)
            if point1 is None and point2 is None:
                kill_map.append(pos)
                board_tmp[pos] = None
                continue
            if point1 is not None and point2 is not None:
                print(pos, point1, point2)
                raise ValueError("ALL NOT NONE")

            for dx, dy in ((0, 0), (0, 1), (1, 0), (1, 1)):
                point = GridPoint(pos.row + dx, pos.col + dy)
                extension_point = link_pos2gridPoint(board_tmp, self.pos, point)
                if extension_point is None:
                    continue
                if extension_point in [point1, point2]:
                    break
                if extension_point not in edge:
                    extension_point = None
                    continue
                break

            if extension_point is None:
                raise ValueError("ALL NONE ERROR")

            extension_edge = None
            if point1 is not None:
                if extension_point == point1:
                    kill_map.append(pos)
                else:
                    extension_edge = EdgePoint(extension_point, edge.point1)
            elif point2 is not None:
                if extension_point == point2:
                    kill_map.append(pos)
                else:
                    extension_edge = EdgePoint(extension_point, edge.point2)
            else:
                raise ValueError()
            if extension_edge:
                remap_pos[pos] = extension_edge

            board_tmp[pos] = None

        if edge_on_pos is not None:
            board_tmp[edge_on_pos] = None
        if edge_on_pos is not None:
            edge_on_var = board.get_variable(edge_on_pos)
        else:
            edge_on_var = True

        get_logger().trace(f"{self.pos}, {edge}, hight:{hight}, kill_map:{kill_map}, remap_pos:{remap_pos}")
        for kill_pos in kill_map:
            model.add(result_var == 0).only_enforce_if(board.get_variable(kill_pos))

        get_logger().trace(f"[{self.pos}]({edge}) if all not {kill_map + list(remap_pos.keys())} var -> {int(ub * hight)}")
        enforce = [
            board.get_variable(kill_pos).Not()
            for kill_pos in kill_map + list(remap_pos.keys())
        ]
        if edge_on_pos:
            enforce.append(edge_on_var)
        model.add(result_var == int(ub * hight)).only_enforce_if(enforce)
        if edge_on_pos:
            get_logger().trace(f"[{self.pos}]({edge}) if {edge_on_pos} is not mines -> 0")
            model.add(result_var == 0).only_enforce_if(edge_on_var.Not())

        if not remap_pos:
            return result_var

        kill_all_not = [
            board.get_variable(kill_pos).Not()
            for kill_pos in kill_map
        ]
        for r in range(1, len(remap_pos) + 1):
            for remap_pos_key in itertools.combinations(list(remap_pos.keys()), r):
                remap_pos_value = [remap_pos[k] for k in remap_pos_key]
                if len(remap_pos_value) == 1:
                    length = remap_pos_value[0].length()
                else:
                    intersection_edge = remap_pos_value[0]
                    length = -1
                    for remap_edge in remap_pos_value[1:]:
                        intersection_edge = intersection_edge.intersection(remap_edge)
                        if intersection_edge is None:
                            length = 0
                            break
                        if type(intersection_edge) is GridPoint:
                            length = 0
                            break
                    if length == -1:
                        length = intersection_edge.length()
                if length == -1:
                    raise ValueError("?")
                if length == 0:
                    get_logger().trace(f"[{self.pos}]({edge}) if ON:{remap_pos_key} -> 0")
                    enforce = [
                        board.get_variable(remap_key_pos)
                        for remap_key_pos in remap_pos_key
                    ]
                    model.add(result_var == 0).only_enforce_if(enforce)
                else:
                    get_logger().trace(f"[{self.pos}]({edge}) getNUM if ON: {[
                        remap_key_pos for remap_key_pos in remap_pos_key
                    ]} NOT: {kill_map + [
                        remap_key_pos for remap_key_pos in remap_pos
                        if remap_key_pos not in remap_pos_key
                    ]} -> {int(ub * length * hight)}")
                    enforce = [
                        board.get_variable(remap_key_pos)
                        for remap_key_pos in remap_pos_key
                    ]
                    enforce.extend(kill_all_not)
                    enforce.extend([
                        board.get_variable(remap_key_pos).Not()
                        for remap_key_pos in remap_pos
                        if remap_key_pos not in remap_pos_key
                    ])
                    enforce.append(edge_on_var)
                    get_logger().trace(f"enforce: {enforce}")
                    model.add(result_var == int(ub * length * hight)).only_enforce_if(enforce)

        return result_var

    def _get_edge_range(
        self, board: 'Board',
        edge: 'EdgePoint', pointr: 'GridPoint'
    ) -> Tuple[List[List[Position]], bool]:
        _, is_y = edge.on()
        point1, point2 = edge
        point1_x, point1_y = point1
        point2_x, point2_y = point2
        pointr_x, pointr_y = pointr

        if is_y:
            line1_k = Fraction(pointr_x - point1_x, pointr_y - point1_y)
            line1_b = point1_x - line1_k * point1_y
            line2_k = Fraction(pointr_x - point2_x, pointr_y - point2_y)
            line2_b = point2_x - line2_k * point2_y
        else:
            line1_k = Fraction(pointr_y - point1_y, pointr_x - point1_x)
            line1_b = point1_y - line1_k * point1_x
            line2_k = Fraction(pointr_y - point2_y, pointr_x - point2_x)
            line2_b = point2_y - line2_k * point2_x
        get_logger().trace(f"{{{edge}, {pointr}, ({line1_k}) * x + {line1_b}, ({line2_k}) * x + {line2_b}}}")

        if is_y:
            flag = point1_y <= self.pos.col
            if flag:
                range_tuple = (int(point1_y), self.pos.col + 1)
            else:
                range_tuple = (self.pos.col, int(point1_y))
        else:
            flag = point1_x <= self.pos.row
            if flag:
                range_tuple = (int(point1_x), self.pos.row + 1)
            else:
                range_tuple = (self.pos.row, int(point1_x))

        result_poslist: List[List[Position]] = []

        for x in range(*range_tuple):
            result_poslist.append([])
            x += 0.5
            if (
                x - 0.5 == (self.pos.col if is_y else self.pos.row) and
                ((not line2_k < 0) ^ flag)
            ):
                lb = self.pos.row if is_y else self.pos.col
            else:
                lb = (math.floor(line2_b + line2_k * (math.ceil(x) if line2_k < 0 else math.floor(x))))
            if (
                x - 0.5 == (self.pos.col if is_y else self.pos.row) and
                ((line1_k < 0) ^ flag)
            ):
                ub = (self.pos.row + 1) if is_y else (self.pos.col + 1)
            else:
                ub = math.ceil(line1_b + line1_k * (math.floor(x) if line1_k < 0 else math.ceil(x)))
            if lb < 0:
                raise ValueError("lb < 0")
            for pos_i in range(lb, ub):
                if is_y:
                    result_poslist[-1].append(board.get_pos(pos_i, int(x - 0.5)))
                else:
                    result_poslist[-1].append(board.get_pos(int(x - 0.5), pos_i))

        return result_poslist, flag
