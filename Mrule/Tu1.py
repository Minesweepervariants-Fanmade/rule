#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/20 21:55
# @Author  : DeepSeek Agent
# @FileName: Tu1.py

from typing import List
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template
from minesweepervariants.abs.Mrule import AbstractMinesClueRule, AbstractMinesValue
from minesweepervariants.board import Board, Position
from minesweepervariants.utils.tool import get_logger, get_random

DIR_UP = 1
DIR_DOWN = 2
DIR_LEFT = 4
DIR_RIGHT = 8

ARROW_COMBINATIONS = [
    DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT,
    DIR_UP | DIR_DOWN, DIR_UP | DIR_RIGHT, DIR_UP | DIR_LEFT,
    DIR_DOWN | DIR_RIGHT, DIR_DOWN | DIR_LEFT, DIR_LEFT | DIR_RIGHT,
]

DIR_NAMES = {
    DIR_UP: "↑",
    DIR_DOWN: "↓",
    DIR_LEFT: "←",
    DIR_RIGHT: "→",
}

def get_direction_sequence(pos: Position, direction: int, board: Board) -> List[Position]:
    result = []
    current = pos
    while True:
        if direction == DIR_UP:
            current = current.up()
        elif direction == DIR_DOWN:
            current = current.down()
        elif direction == DIR_LEFT:
            current = current.left()
        elif direction == DIR_RIGHT:
            current = current.right()
        else:
            break
        if not current.in_bounds(board.boundary(current.board_key)):
            break
        result.append(current)
    return result

class RuleTu1(AbstractMinesClueRule):
    id = "Tu1"
    name = "Tu1"
    name.zh_CN = "图棋1"
    doc = "Mine clue indicates the nearest n mines in the arrow direction have value 0."
    doc.zh_CN = "雷线索表示箭头方向最近的n个雷雷值为0。"
    tags = ["Original", "Local", "Mine-Value"]
    creation_time = "2026-07-19"
    author = ("小中医", 3086842243)

    def fill(self, board: 'Board') -> 'Board':
        import random
        logger = get_logger()
        
        # 收集所有雷格位置
        mine_positions = list(board("F"))
        if not mine_positions:
            return board
        
        # 存储每个位置需要设置的雷值
        value_overrides = {}
        
        for pos, _ in mine_positions:
            arrow_mask = random.choice(ARROW_COMBINATIONS)
            n = random.randint(1, 2)
            
            logger.debug(f"[Tu1] fill: pos={pos}, arrow_mask={arrow_mask}, n={n}")
            
            affected_positions = []
            dirs = [DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT]
            for d in dirs:
                if arrow_mask & d:
                    seq = get_direction_sequence(pos, d, board)
                    mine_pos = [p for p in seq if board.get_type(p) == "F"]
                    for p in mine_pos[:n]:
                        if p not in affected_positions:
                            affected_positions.append(p)
            
            # 创建线索对象
            obj = MinesValueTu1(pos, n, arrow_mask, affected_positions)
            board.set_value(pos, obj)
            logger.debug(f"[Tu1] created clue at {pos}: n={n}, arrow_mask={arrow_mask}, affected={len(affected_positions)}")
            
            # 记录需要修改雷值的位置
            for p in affected_positions:
                value_overrides[p] = 0
        
        # 修改受影响位置的雷值
        for p, target_value in value_overrides.items():
            val = board.get_value(p)
            if val is not None and hasattr(val, 'value'):
                # 修改雷值
                if isinstance(val.value, SingleIntValue):
                    val.value.value = target_value
                else:
                    val.value = SingleIntValue(target_value, is_mine=True)
                logger.debug(f"[Tu1] 设置位置 {p} 的雷值为 {target_value}")
            else:
                logger.warning(f"[Tu1] 无法修改位置 {p} 的雷值: val={val}")
        
        return board

class MinesValueTu1(AbstractMinesValue):
    id = RuleTu1.id
    def __init__(self, pos: 'Position', n: int = 1, arrow_mask: int = DIR_UP,
                 affected_positions: List['Position'] = None):
        self.pos = pos
        self.n = n
        self.arrow_mask = arrow_mask
        self.affected_positions = affected_positions if affected_positions is not None else []
        self.value = SingleIntValue(1, is_mine=True)
    def __repr__(self):
        arrow_str = "".join(
            DIR_NAMES[d] for d in [DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT] if self.arrow_mask & d
        )
        return f"{arrow_str}{self.n}"
    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)
        if isinstance(_data, dict):
            n = _data.get("n", 1)
            arrow_mask = _data.get("arrow_mask", DIR_UP)
            affected_positions_data = _data.get("affected_positions", [])
            affected_positions = []
            for p_data in affected_positions_data:
                if isinstance(p_data, list) and len(p_data) >= 2:
                    col, row = p_data[0], p_data[1]
                    board_key = p_data[2] if len(p_data) > 2 else None
                    affected_positions.append(Position(col, row, board_key))
            return cls(pos, n, arrow_mask, affected_positions)
        if is_value_template(_data):
            return cls(pos, 1, DIR_UP, [])
        raise TypeError("Invalid data format for MinesValueTu1")
    def json(self):
        affected_positions_data = [
            [p.col, p.row, p.board_key] for p in self.affected_positions
        ]
        return {
            "n": self.n,
            "arrow_mask": self.arrow_mask,
            "affected_positions": affected_positions_data,
        }
    def high_light(self, board: 'Board') -> list['Position']:
        return list(self.affected_positions)
    def create_constraints(self, board: 'Board', switch):
        logger = get_logger()
        logger.trace(f"[Tu1] {self} - values already set in fill, no constraints added")
    def weaker(self, board: 'Board') -> 'AbstractValue':
        if self.n > 1:
            new_n = self.n - 1
            return MinesValueTu1(self.pos, new_n, self.arrow_mask, self.affected_positions)
        else:
            dirs = [DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT]
            active_dirs = [d for d in dirs if self.arrow_mask & d]
            if len(active_dirs) > 1:
                new_mask = self.arrow_mask & ~active_dirs[0]
                return MinesValueTu1(self.pos, self.n, new_mask, self.affected_positions)
            elif len(active_dirs) == 1:
                return MinesValueTu1(self.pos, self.n, 0, self.affected_positions)
            else:
                return self
    def weaker_times(self) -> int:
        dirs = [DIR_UP, DIR_DOWN, DIR_LEFT, DIR_RIGHT]
        active_dirs = [d for d in dirs if self.arrow_mask & d]
        return (self.n - 1) + len(active_dirs)
