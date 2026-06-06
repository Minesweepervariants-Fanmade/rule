#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/05/12 13:37
# @Author  : Wu_RH
# @FileName: 1EatStar.py
import time
from typing import List, Tuple, cast

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.abs.rule import AbstractValue
from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue
from minesweepervariants.board import JSONObject, Board, Position
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.impl_obj import MINES_TAG, VALUE_QUESS
from minesweepervariants.utils.value_template import Template, SingleIntValue, is_value_template


def grid_cells_between(
    board:Board,
    start: Position,
    end: Position
) -> List[Position]:
    """
    返回从 start 方格中心到 end 方格中心连线所经过的所有方格（包含两端）。
    start, end = (row, col) 整数索引。
    返回列表 [(row,col), ...]
    """
    if start.board_key != end.board_key:
        return []
    r1, c1 = start.x, start.y
    r2, c2 = end.x, end.y

    # 放大坐标（中心变为奇数）
    x1, y1 = 2*c1 + 1, 2*r1 + 1
    x2, y2 = 2*c2 + 1, 2*r2 + 1

    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    step_x = 1 if x2 > x1 else -1
    step_y = 1 if y2 > y1 else -1

    # 到下一网格线的距离（在放大坐标下，网格线间距为 2）
    # 但因为我们从奇数中心出发，到最近的偶数网格线距离为 1
    t_max_x = 1.0 / dx if dx != 0 else float('inf')
    t_max_y = 1.0 / dy if dy != 0 else float('inf')
    t_delta_x = 2.0 / dx if dx != 0 else float('inf')
    t_delta_y = 2.0 / dy if dy != 0 else float('inf')

    cells = []
    x, y = x1, y1
    cur_r, cur_c = r1, c1
    cells.append(board.get_pos(cur_r, cur_c, key=start.board_key))

    eps = 1e-12
    while (x, y) != (x2, y2):
        if t_max_x < t_max_y - eps:
            # 穿过垂直网格线
            cur_c += step_x
            x = x2 if abs(x + step_x*2 - x2) < 2 else x + step_x*2  # 精确移动
            t_max_x += t_delta_x
        elif t_max_y < t_max_x - eps:
            # 穿过水平网格线
            cur_r += step_y
            y = y2 if abs(y + step_y*2 - y2) < 2 else y + step_y*2
            t_max_y += t_delta_y
        else:
            # 同时穿过水平和垂直网格线（角点）
            # 添加横向邻居 (cur_c+step_x, cur_r)
            cells.append(board.get_pos(cur_r, cur_c + step_x, key=end.board_key))
            # 添加纵向邻居 (cur_c, cur_r+step_y)
            cells.append(board.get_pos(cur_r + step_y, cur_c, key=end.board_key))
            # 再移动至对角方格
            cur_c += step_x
            cur_r += step_y
            cells.append(board.get_pos(cur_r, cur_c, key=end.board_key))
            # 更新坐标和 t 值
            x = x2 if abs(x + step_x * 2 - x2) < 2 else x + step_x * 2
            y = y2 if abs(y + step_y * 2 - y2) < 2 else y + step_y * 2
            t_max_x += t_delta_x
            t_max_y += t_delta_y
        cells.append(board.get_pos(cur_r, cur_c, key=end.board_key))

    # 去重（如果终点重复添加则删除最后一个）
    if cells[-1] != (r2, c2):
        cells.append(board.get_pos(r2, c2, key=start.board_key))
    return cells


class Rule1EatStar(AbstractClueRule):
    id = "1E*"
    name = "Eyesight@*"
    name.zh_CN = "视野@*"
    doc = ("The clue value indicates the number of grid cell centers visible from the clue,"
           " with line of sight blocked by mines (including boundaries).")
    doc.zh_CN = "线索值表示线索能看到的格中心点数，视线会被雷（包括边界）阻挡"
    creation_time = "2026-04-30 03:00:53"
    tags = ["Creative", "Local", "Extensive Trial", "Number Clue"]
    author = ("NT", 2201963934)

    def fill(self, board: 'Board') -> 'Board':
        for board_key in board.get_interactive_keys():
            line_map = {}
            positions = [pos for pos, _ in board(key=board_key)]
            for start_index in range(len(positions)):
                start_pos = positions[start_index]
                for end_pos in positions[start_index + 1:]:
                    line = grid_cells_between(board, start_pos, end_pos)
                    line_map[(start_pos, end_pos)] = "F" not in board.batch(line, "type")
            for pos, _ in board("N", key=board_key):
                value = sum(line_map[key] for key in line_map if pos in key) + 1
                board[pos] = Value1EatStar(pos, value)
        return board


class Value1EatStar(AbstractClueValue):
    id = Rule1EatStar.id

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

    def high_light(self, board: 'Board') -> List['Position'] | None:
        high_lights = []
        for pos, _ in board(mode="var", key=self.pos.board_key):
            line = grid_cells_between(board, self.pos, pos)
            if "F" in board.batch(line, mode="type"):
                continue
            high_lights.extend(line + [pos])
        return list(set(high_lights))

    def create_constraints(self, board: 'Board', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)

        count_list = []
        for pos, var in board(mode="var", key=self.pos.board_key):
            line = grid_cells_between(board, self.pos, pos)
            var_list = set(board.batch(line, mode="var") + [var])
            if "F" in board.batch(line, mode="type"):
                continue
            if None in var_list:
                continue
            count_swtich = model.new_bool_var(f"1E*_{self.pos}_{pos}")
            count_list.append(count_swtich)
            model.add_bool_and([var.Not() for var in var_list]).OnlyEnforceIf(s, count_swtich)
            model.add_bool_or(var_list).OnlyEnforceIf(s, count_swtich.Not())
        model.add(sum(count_list) == self.value.value).OnlyEnforceIf(s)