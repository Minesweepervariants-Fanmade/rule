#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Author  : NT (2201963934)
# @FileName: AR.py
"""
[AR] 箭雷：
每个雷格有八个方向之一的箭头，线索数表示箭头方向射线指向它的雷的个数。
额外要求每个雷的箭头至少指向一个非雷格。

参数 ! : 添加三个主板同大小的额外主板，
原主板格中的雷对应三个额外主板同位格的雷视为布尔变量
共同映射到其方向编码（三个格分别表示+180°，+90°，+45°），
非雷则均为非雷。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional
from collections import defaultdict

from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import JSONObject, deep_unwrap
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template
from minesweepervariants.board import Board, Position, MASTER_BOARD_KEY

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....utils.tool import get_logger, get_random
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG

if TYPE_CHECKING:
    from ....impl.summon.solver import Switch


# 8 方向 (行偏移, 列偏移)，从上方开始顺时针 45° 递增：
# 0=上, 1=右上, 2=右, 3=右下, 4=下, 5=左下, 6=左, 7=左上
DIRECTIONS: List[tuple] = [
    (-1, 0),
    (-1, 1),
    (0, 1),
    (1, 1),
    (1, 0),
    (1, -1),
    (0, -1),
    (-1, -1),
]

# 三个副板 key
AUX_180 = "AR_a"  # 表示 +180°
AUX_90 = "AR_b"   # 表示 +90°
AUX_45 = "AR_c"   # 表示 +45°
AUX_KEYS = (AUX_180, AUX_90, AUX_45)


def ray_positions(board: Board, pos: Position, direction: int) -> List[Position]:
    """返回 pos 沿 direction 方向射线经过的所有格子（不含自身）。"""
    dx, dy = DIRECTIONS[direction]
    result: List[Position] = []
    cur = pos.shift(dy, dx)  # shift(col, row)
    while board.in_bounds(cur):
        result.append(cur)
        cur = cur.shift(dy, dx)
    return result


class RuleAR(AbstractClueRule):
    id = "AR"
    name = "Arrow"
    name.zh_CN = "箭雷"
    doc = ("Each mine cell has an arrow in one of eight directions. "
           "The clue value indicates the number of mines whose arrow ray points to it. "
           "Additionally, each mine's arrow must point to at least one non-mine cell.")
    doc.zh_CN = ("每个雷格有八个方向之一的箭头，线索数表示箭头方向射线指向它的雷的个数。"
                 "额外要求每个雷的箭头至少指向一个非雷格。")
    tags = ["Creative", "Local", "Number Clue", "Arrow Clue"]
    creation_time = "2026-10-14"
    author = ("NT", 2201963934)

    def __init__(self, board: Optional[Board] = None, data: Optional[str] = None) -> None:
        super().__init__(board, data)
        self.use_aux = (data == "!")
        if board is None or not self.use_aux:
            return
        size = board.get_config(MASTER_BOARD_KEY, "size")
        for name in AUX_KEYS:
            board.generate_board(name, size=size)
            board.set_config(name, "VALUE", VALUE_QUESS)
            board.set_config(name, "MINES", MINES_TAG)

    def init_clear(self, board: Board, vice_board: bool) -> None:
        if not self.use_aux:
            return
        for name in AUX_KEYS:
            for pos, _ in board("F" if vice_board else "CF", key=name):
                board.set_value(pos, None)

    # ------------------------------------------------------------------
    # fill
    # ------------------------------------------------------------------
    def fill(self, board: Board) -> Board:
        logger = get_logger()
        random = get_random()

        # 1. 为每个雷分配方向
        mine_positions = [pos for pos, _ in board("F", special='raw', key=MASTER_BOARD_KEY)]
        if not mine_positions:
            return board
        directions: dict = {}
        for m in mine_positions:
            valid_dirs: List[int] = []
            for d in range(8):
                ray = ray_positions(board, m, d)
                if not ray:
                    continue
                if any(board.get_type(p, special='raw') != "F" for p in ray):
                    valid_dirs.append(d)
            if valid_dirs:
                directions[m] = random.choice(valid_dirs)
            else:
                # 无有效方向，随机挑一个使后续约束无解并重试
                directions[m] = random.randint(0, 7)
                logger.warning(f"[AR] mine {m} has no valid direction (ray all mines or empty)")

        # 2. 填充副板（! 模式）
        if self.use_aux:
            for name in AUX_KEYS:
                for pos, _ in board(key=name):
                    board.set_value(pos, VALUE_QUESS)
            for m, d in directions.items():
                bits = ((d >> 2) & 1, (d >> 1) & 1, d & 1)
                for name, bit in zip(AUX_KEYS, bits):
                    p = board.get_pos(m.row, m.col, name)
                    if p is not None:
                        board.set_value(p, MINES_TAG if bit else VALUE_QUESS)

        # 3. 计算每个非雷格被指向的次数
        counts: dict = {}
        for m, d in directions.items():
            for p in ray_positions(board, m, d):
                if board.get_type(p, special='raw') == "F":
                    continue
                counts[p] = counts.get(p, 0) + 1

        # 4. 填充线索
        for pos, _ in board("N", special='raw', key=MASTER_BOARD_KEY):
            board.set_value(pos, ValueAR(pos, count=counts.get(pos, 0)))

        return board

    # ------------------------------------------------------------------
    # create_constraints
    # ------------------------------------------------------------------
    def create_constraints(self, board: Board, switch: "Switch") -> None:
        model = board.get_model()
        s = switch.get(model, self)
        logger = get_logger()

        all_positions = [pos for pos, _ in board(key=MASTER_BOARD_KEY)]
        pos_to_mine_var: dict = {}
        for pos in all_positions:
            v = board.get_variable(pos, special='raw')
            if v is not None:
                pos_to_mine_var[pos] = v

        # -------------- 方向变量 -------------- #
        dir_vars: dict = {}

        if self.use_aux:
            # 方向由副板三个位的 3-bit 编码给出：d = a*4 + b*2 + c
            for pos in all_positions:
                p_a = board.get_pos(pos.row, pos.col, AUX_180)
                p_b = board.get_pos(pos.row, pos.col, AUX_90)
                p_c = board.get_pos(pos.row, pos.col, AUX_45)
                if p_a is None or p_b is None or p_c is None:
                    continue
                v_a = board.get_variable(p_a)
                v_b = board.get_variable(p_b)
                v_c = board.get_variable(p_c)
                if v_a is None or v_b is None or v_c is None:
                    continue
                mine_v = pos_to_mine_var.get(pos)
                if mine_v is not None:
                    # 原主板非雷 => 三个副板位均为 0
                    model.add(v_a == 0).only_enforce_if([mine_v.Not(), s])
                    model.add(v_b == 0).only_enforce_if([mine_v.Not(), s])
                    model.add(v_c == 0).only_enforce_if([mine_v.Not(), s])
                d_var = model.new_int_var(0, 7, f"AR_dir_{pos.row}_{pos.col}")
                model.add(d_var == v_a * 4 + v_b * 2 + v_c).only_enforce_if(s)
                dir_vars[pos] = d_var
        else:
            for pos in all_positions:
                d_var = model.new_int_var(0, 7, f"AR_dir_{pos.row}_{pos.col}")
                mine_v = pos_to_mine_var.get(pos)
                if mine_v is not None:
                    # 非雷格的方向无意义，固定为 0 缩小搜索空间
                    model.add(d_var == 0).only_enforce_if([mine_v.Not(), s])
                dir_vars[pos] = d_var

        # -------------- “每个雷的箭头至少指向一个非雷格” -------------- #
        for m in all_positions:
            mine_v = pos_to_mine_var.get(m)
            d_var = dir_vars.get(m)
            if mine_v is None or d_var is None:
                continue
            for d in range(8):
                ray = ray_positions(board, m, d)

                d_eq = model.new_bool_var(f"AR_deq_{m.row}_{m.col}_{d}")
                model.add(d_var == d).only_enforce_if([d_eq, s])
                model.add(d_var != d).only_enforce_if([d_eq.Not(), s])

                if not ray:
                    # 射线为空：不能取该方向
                    model.add(d_eq == 0).only_enforce_if([mine_v, s])
                    continue

                ray_vars = [pos_to_mine_var[p] for p in ray if p in pos_to_mine_var]
                if not ray_vars:
                    model.add(d_eq == 0).only_enforce_if([mine_v, s])
                    continue

                # all_mine == AND(ray_vars)
                all_mine = model.new_bool_var(f"AR_am_{m.row}_{m.col}_{d}")
                model.add_bool_and(ray_vars).only_enforce_if([all_mine, s])
                model.add_bool_or([v.Not() for v in ray_vars]).only_enforce_if([all_mine.Not(), s])

                # mine_v AND d_eq => NOT all_mine
                model.add_bool_or([mine_v.Not(), d_eq.Not(), all_mine.Not()]).only_enforce_if(s)

        # -------------- 线索格被指向数量 -------------- #
        incoming: dict = defaultdict(list)
        for m in all_positions:
            for d in range(8):
                for p in ray_positions(board, m, d):
                    incoming[p].append((m, d))

        for p in all_positions:
            obj = board.get_value(p)
            if not isinstance(obj, ValueAR):
                continue

            mine_v_p = pos_to_mine_var.get(p)
            if mine_v_p is not None:
                model.add(mine_v_p == 0).only_enforce_if(s)

            count_terms = []
            for (m, d) in incoming.get(p, []):
                mine_v_m = pos_to_mine_var.get(m)
                d_var_m = dir_vars.get(m)
                if mine_v_m is None or d_var_m is None:
                    continue

                d_eq = model.new_bool_var(f"AR_heq_{p.row}_{p.col}_{m.row}_{m.col}_{d}")
                model.add(d_var_m == d).only_enforce_if([d_eq, s])
                model.add(d_var_m != d).only_enforce_if([d_eq.Not(), s])

                hit = model.new_bool_var(f"AR_hit_{p.row}_{p.col}_{m.row}_{m.col}_{d}")
                # hit == mine_v_m AND d_eq
                model.add(hit <= mine_v_m).only_enforce_if(s)
                model.add(hit <= d_eq).only_enforce_if(s)
                model.add(hit >= mine_v_m + d_eq - 1).only_enforce_if(s)
                count_terms.append(hit)

            if count_terms:
                model.add(sum(count_terms) == obj.count).only_enforce_if(s)
            else:
                model.add(obj.count == 0).only_enforce_if(s)

        logger.trace(f"[AR] constraints added (aux={self.use_aux})")


class ValueAR(AbstractClueValue):
    id = RuleAR.id

    def __init__(self, pos: Position, count: int = 0):
        super().__init__(pos, b'')
        self.count = count
        self.value = SingleIntValue(count)

    @classmethod
    def from_json(cls, pos: Position, data: JSONObject) -> AbstractValue:
        _data = deep_unwrap(data)
        if not is_value_template(_data):
            raise TypeError()
        v = SingleIntValue.try_from(_data)
        if v is None:
            raise ValueError()
        return cls(pos, count=v.value)

    def __repr__(self) -> str:
        return str(self.count)
