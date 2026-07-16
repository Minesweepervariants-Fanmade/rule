#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/17
# @Author  : NT (2201963934)
# @FileName: VQM.py
"""
[V?] 经典扫雷？：数字线索表示周围八个中的雷或非雷数
"""
from functools import cache
from typing import cast, Self
from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import JSONObject, deep_unwrap
from minesweepervariants.position_set import PositionSet
from minesweepervariants.utils.tool import get_logger, get_random
from minesweepervariants.utils.value_template import SingleIntValue, Template, is_value_template
from minesweepervariants.utils.impl_obj import VALUE_QUESS, MINES_TAG


@cache
def neighbors() -> PositionSet:
    """返回8方向邻居的相对位置集合"""
    return PositionSet(Position(0, 0).neighbors(2))


class DataVQM(SingleIntValue):
    """扩展SingleIntValue，添加mode字段表示该线索表示雷数(True)还是非雷数(False)"""

    def __init__(self, value: int, mode: bool):
        super().__init__(value, False)
        self.mode: bool = mode

    def _template(self) -> Template:
        result = super()._template()
        result["_SingleIntValue"] = True
        result["data"] = self.value
        result["mode"] = self.mode
        return result

    @classmethod
    def try_from(cls, data: Template) -> Self | None:
        if not data.get("_SingleIntValue", False):
            return None
        value = cast(int, data["data"])
        mode = cast(bool, data.get("mode", False))
        return cls(value, mode)


class RuleVQM(AbstractClueRule):
    id = "V?"
    name = "Vanilla Question"
    name.zh_CN = "经典扫雷？"  # type: ignore[attr-defined]
    doc = "Each number indicates either the number of mines or non-mines in the surrounding eight cells"
    doc.zh_CN = "数字线索表示周围八个中的雷或非雷数"  # type: ignore[attr-defined]
    tags = ["Original", "Local", "Vanilla Variant", "Number Clue", "Variant"]
    creation_time = "2026-07-17"
    author = ("NT", 2201963934)

    def fill(self, board: 'Board') -> 'Board':
        rng = get_random()
        for pos, _ in board("N", special='raw'):
            # 获取有效邻居列表
            valid_neighbors: list[Position] = []
            for rel_pos in neighbors():
                neighbor = rel_pos.deviation(pos)
                neighbor.to_board(pos.board_key)
                if board.is_valid(neighbor):
                    valid_neighbors.append(neighbor)

            # 统计雷数和邻居数
            mine_count = sum(1 for p in valid_neighbors if board.get_type(p) == "F")
            neighbor_count = len(valid_neighbors)
            non_mine_count = neighbor_count - mine_count

            # 随机选择模式
            mode = rng.choice([True, False])
            count = mine_count if mode else non_mine_count

            board.set_value(pos, ValueVQM(pos, count=count, mode=mode, valid_neighbors=valid_neighbors))
        return board


class ValueVQM(AbstractClueValue):
    id = RuleVQM.id

    def __init__(
        self,
        pos: Position,
        count: int = 0,
        mode: bool = True,
        valid_neighbors: list[Position] | None = None
    ):
        super().__init__(pos, b'')
        self.count = count
        self.mode = mode
        self.value = DataVQM(count, mode)
        if valid_neighbors is not None:
            self._valid_neighbors = valid_neighbors
        else:
            # 备用计算（通常不会用到，因为fill会传入）
            self._valid_neighbors = []
            for rel_pos in neighbors():
                neighbor = rel_pos.deviation(pos)
                neighbor.to_board(pos.board_key)
                if pos.board_key == neighbor.board_key:
                    self._valid_neighbors.append(neighbor)
        self.neighbor_count = len(self._valid_neighbors)

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)
        if not is_value_template(_data):
            raise TypeError()
        template_data = cast(Template, _data)
        value_obj = DataVQM.try_from(template_data)
        if value_obj is None:
            raise ValueError()
        return cls(pos, count=value_obj.value, mode=value_obj.mode, valid_neighbors=None)

    def _get_valid_neighbors(self, board: 'Board') -> list[Position]:
        """获取有效邻居列表（优先使用存储的，否则动态计算）"""
        if self._valid_neighbors:
            # 过滤掉可能因board变化而失效的位置（但通常不会变）
            return [p for p in self._valid_neighbors if board.is_valid(p)]
        # 动态计算
        result: list[Position] = []
        for rel_pos in neighbors():
            neighbor = rel_pos.deviation(self.pos)
            neighbor.to_board(self.pos.board_key)
            if board.is_valid(neighbor):
                result.append(neighbor)
        return result

    def high_light(self, board: 'Board') -> list['Position']:
        return self._get_valid_neighbors(board)

    def invalid(self, board: 'Board') -> bool:
        valid_neighbors = self._get_valid_neighbors(board)
        return board.batch(valid_neighbors, mode="type", special='raw').count("N") == 0

    def deduce_cells(self, board: 'Board') -> bool:
        # 快速推理（与V相同）
        valid_neighbors = self._get_valid_neighbors(board)
        type_dict: dict[str, list[Position]] = {"N": [], "F": []}
        for pos in valid_neighbors:
            t = board.get_type(pos)
            if t in ("", "C"):
                continue
            type_dict[t].append(pos)
        n_num = len(type_dict["N"])
        f_num = len(type_dict["F"])
        if n_num == 0:
            return False
        if f_num == self.count:
            for i in type_dict["N"]:
                board.set_value(i, VALUE_QUESS)
            return True
        if f_num + n_num == self.count:
            for i in type_dict["N"]:
                board.set_value(i, MINES_TAG)
            return True
        return False

    def create_constraints(self, board: 'Board', switch: Switch):
        """
        创建CP-SAT约束：
        若 mode == True: count == 周围雷数总和
        若 mode == False: count == 周围非雷数总和 (有效邻居数 - 雷数总和)
        """
        model = board.get_model()
        logger = get_logger()

        # 获取有效邻居
        valid_neighbors = self._get_valid_neighbors(board)
        if not valid_neighbors:
            return

        # 收集邻居变量
        neighbor_vars: list[IntVar] = []
        for neighbor in valid_neighbors:
            var = board.get_variable(neighbor)
            if var is not None:
                neighbor_vars.append(var)
            else:
                logger.warning(f"[V?] Value[{self.pos}] skipped: neighbor {neighbor} has no variable")
                return

        if len(neighbor_vars) != len(valid_neighbors):
            logger.warning(f"[V?] Value[{self.pos}] skipped: variable count mismatch")
            return

        s = switch.get(model, self.pos)
        if not neighbor_vars:
            return

        # 雷数总和
        mine_sum = sum(neighbor_vars)

        if self.mode:
            # 表示雷数：count == mine_sum
            model.add(mine_sum == self.count).OnlyEnforceIf(s)
            logger.trace(f"[V?] Value[{self.pos}: {self.count}] (mode=mine) add: sum({neighbor_vars}) == {self.count}")
        else:
            # 表示非雷数：count == neighbor_count - mine_sum
            neighbor_count = len(valid_neighbors)
            model.add(mine_sum == (neighbor_count - self.count)).OnlyEnforceIf(s)
            logger.trace(
                f"[V?] Value[{self.pos}: {self.count}] (mode=non-mine, neighbor_count={neighbor_count}) "
                f"add: sum({neighbor_vars}) == {neighbor_count - self.count}"
            )
