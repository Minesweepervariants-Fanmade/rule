#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/08/07 22:21
# @Author  : Wu_RH
# @FileName: UP.py
"""
[UP]唯一路径(Unique Path): 线索格表示从这个格开始只能往右或下走，到达右下角的方法数。
"""
import math
from typing import List, Optional

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import JSONObject, deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, SingleIntValue
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.solver import Switch


class RuleUP(AbstractClueRule):
    id = "UP"
    name = "Unique Path"
    name.zh_CN = "唯一路径"
    doc = "Clue shows the number of ways to go from this cell to the bottom-right corner, moving only right or down"
    doc.zh_CN = "线索格表示从这个格开始只能往右或下走，到达右下角的方法数。"
    tags = ["Creative", "Local", "Number Clue", "Construction"]
    creation_time = "2025-08-07"
    author = ("", 0)

    def fill(self, board: 'Board') -> 'Board':
        for key in board.get_interactive_keys():
            root_pos = board.boundary(key)
            # 从右下角开始遍历，确保下方和右方的值已计算
            for col_pos in board.get_col_pos(root_pos)[::-1]:
                for pos in board.get_row_pos(col_pos)[::-1]:
                    if board.get_type(pos) != "N":
                        continue
                    value = 0
                    # 累加下方线索的值
                    if board.in_bounds(pos.down()):
                        down_pos = pos.down()
                        if board.get_type(down_pos) == "C":
                            obj = board[down_pos]
                            if isinstance(obj, ValueUP):
                                value += obj.count
                    # 累加右方线索的值
                    if board.in_bounds(pos.right()):
                        right_pos = pos.right()
                        if board.get_type(right_pos) == "C":
                            obj = board[right_pos]
                            if isinstance(obj, ValueUP):
                                value += obj.count
                    # 如果下方和右方都在边界外（右下角），路径数为1
                    if not board.in_bounds(pos.down()) and not board.in_bounds(pos.right()):
                        value = 1
                    obj = ValueUP(pos, count=value)
                    board[pos] = obj
        return board

    def create_constraints(self, board: 'Board', switch: 'Switch'):
        model = board.get_model()
        # 存储每个位置的DP变量，供ValueUP使用
        board._dp_map = {}

        for key in board.get_interactive_keys():
            ub_x = board.boundary(key).x
            ub_y = board.boundary(key).y
            pos_var_map = {}

            # 为每个位置创建DP变量
            for pos, var in board(mode="variable", key=key):
                x, y = pos.x, pos.y
                ub = math.comb(ub_x - x + ub_y - y, ub_y - y)
                pos_var_map[pos] = model.new_int_var(0, ub, f"{pos}:dp")
                # 如果该位置是雷，DP值为0
                model.add(pos_var_map[pos] == 0).OnlyEnforceIf(var)

            # 存储到board临时属性
            board._dp_map[key] = pos_var_map

            # 添加DP递推约束
            for pos, var in board(mode="variable", key=key):
                var_d = 0
                var_r = 0
                if board.in_bounds(pos.down()):
                    var_d = pos_var_map[pos.down()]
                if board.in_bounds(pos.right()):
                    var_r = pos_var_map[pos.right()]
                if board.boundary(key) == pos:
                    # 右下角：路径数为1
                    model.add(pos_var_map[pos] == 1).OnlyEnforceIf(var.Not())
                else:
                    # 其他位置：路径数 = 下方路径数 + 右方路径数
                    model.add(pos_var_map[pos] == var_d + var_r).OnlyEnforceIf(var.Not())

            # 为每个线索添加约束
            for pos, _ in board(mode="type", key=key):
                obj = board[pos]
                if isinstance(obj, ValueUP):
                    obj.create_constraints(board, switch)

        # 清理临时属性
        delattr(board, '_dp_map')


class ValueUP(AbstractClueValue):
    id = RuleUP.id

    def __init__(self, pos: 'Position', count: int = 0):
        super().__init__(pos, b'')
        self.count = count
        self.value = SingleIntValue(count)

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        """从JSON数据反序列化ValueUP对象"""
        _data = deep_unwrap(data)
        # 尝试解析为SingleIntValue
        value = SingleIntValue.try_from(_data)
        if value is not None:
            return cls(pos, count=value.value)
        # 兼容旧数据格式（直接存储整数）
        if isinstance(_data, (int, float)):
            return cls(pos, count=int(_data))
        raise ValueError(f"Invalid data for ValueUP: {_data}")

    def __repr__(self):
        return str(self.count)

    def high_light(self, board: 'Board', pos: Optional['Position'] = None) -> List['Position'] | None:
        if pos is None:
            pos = self.pos
        if board.get_type(pos) != "C":
            return [pos]
        positions = {pos}
        # 递归高亮下方和右方的路径
        if board.in_bounds(pos.down()):
            for _pos in self.high_light(board, pos.down()):
                positions.add(_pos)
        if board.in_bounds(pos.right()):
            for _pos in self.high_light(board, pos.right()):
                positions.add(_pos)
        return list(positions)

    def code(self) -> bytes:
        return bytes([self.count])

    def create_constraints(self, board: 'Board', switch: 'Switch'):
        """创建CP-SAT约束: DP变量等于线索值"""
        model = board.get_model()
        # 从board的临时属性中获取DP变量
        dp_map = getattr(board, '_dp_map', {}).get(self.pos.board_key, {})
        dp_var = dp_map.get(self.pos)
        if dp_var is None:
            return
        # 添加约束：DP变量 == 线索值
        model.add(dp_var == self.count).OnlyEnforceIf(switch.get(model, self.pos))
