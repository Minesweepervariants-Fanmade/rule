#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
[1Eエ] 竖直远视野 (Vertical Farsight)：
线索表示竖直视野格和上下两个方向远视野格总数（相同格不重复计算）。

- 竖直视野格：线索格自身，以及沿上、下方向连续的非雷格，遇雷或题板边界停止（包含自身）。
- 上下两个方向的远视野格：按 [1F] 定义，从线索格沿该方向前进，直到遇到雷或题版边界，
  取该方向路径上最后一个非雷格（若线索格紧邻雷或越界，则为线索格自身），
  再统计该格所在行上左右连续的非雷格（包含该格本身，遇雷或边界停止）。
- 三者并集的大小即线索值（相同格不重复计算）。
"""

from typing import List, Set

from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import JSONObject, deep_unwrap
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position
from ....utils.tool import get_logger


def _up_path(board: Board, pos: Position) -> Position:
    """返回上方路径上的最后一个非雷位置（含 pos 自身）。"""
    cur = pos.clone()
    while True:
        nxt = cur.up()
        if not board.in_bounds(nxt) or board.get_type(nxt) == "F":
            return cur
        cur = nxt


def _down_path(board: Board, pos: Position) -> Position:
    """返回下方路径上的最后一个非雷位置（含 pos 自身）。"""
    cur = pos.clone()
    while True:
        nxt = cur.down()
        if not board.in_bounds(nxt) or board.get_type(nxt) == "F":
            return cur
        cur = nxt


def _row_span(board: Board, start: Position) -> Set[Position]:
    """以 start 所在行为准，向左右扩展连续非雷格（含 start）。"""
    result: Set[Position] = {start}
    cur = start.clone()
    while True:
        nxt = cur.left()
        if not board.in_bounds(nxt) or board.get_type(nxt) == "F":
            break
        result.add(nxt)
        cur = nxt
    cur = start.clone()
    while True:
        nxt = cur.right()
        if not board.in_bounds(nxt) or board.get_type(nxt) == "F":
            break
        result.add(nxt)
        cur = nxt
    return result


def _vertical_span(board: Board, pos: Position) -> Set[Position]:
    """线索格自身 + 上下连续非雷格（遇雷或边界停止）。"""
    result: Set[Position] = {pos}
    cur = pos.clone()
    while True:
        nxt = cur.up()
        if not board.in_bounds(nxt) or board.get_type(nxt) == "F":
            break
        result.add(nxt)
        cur = nxt
    cur = pos.clone()
    while True:
        nxt = cur.down()
        if not board.in_bounds(nxt) or board.get_type(nxt) == "F":
            break
        result.add(nxt)
        cur = nxt
    return result


def calc_value(board: Board, pos: Position) -> int:
    """计算 [1Eエ] 的线索值。"""
    v = _vertical_span(board, pos)
    u = _row_span(board, _up_path(board, pos))
    d = _row_span(board, _down_path(board, pos))
    return len(v | u | d)


class Rule1Ee(AbstractClueRule):
    id = "1Eエ"
    name = "Vertical Farsight"
    name.zh_CN = "竖直远视野"  # type: ignore[attr-defined]
    doc = ("The clue value is the number of distinct cells in the union of: "
           "(1) the vertical eyesight cells of the clue (itself plus consecutive non-mine cells upward "
           "and downward, stopping at a mine or the board edge), and "
           "(2) for each of the up and down directions, the Farsight [1F] cells: the row of the farthest "
           "non-mine cell reached before a mine or the board edge, extending left and right through "
           "consecutive non-mine cells.")
    doc.zh_CN = ("线索表示竖直视野格和上下两个方向远视野格总数（相同格不重复计算）。"
                 "竖直视野格指线索格自身及上下连续非雷格（遇雷或边界停止）；"
                 "每个方向的远视野格用[1F]定义：走到该方向的雷或题版边界，取最后一个非雷格，"
                 "再统计该格所在行左右连续的非雷格。三者并集的大小为线索值。")  # type: ignore[attr-defined]
    tags = ["Creative", "Local", "Number Clue", "Arrow Clue"]
    creation_time = "2026-08-10"
    author = ("NT", 2201963934)

    def fill(self, board: 'Board') -> 'Board':
        for pos, _ in board("N", special='raw'):
            board.set_value(pos, Value1Ee(pos, count=calc_value(board, pos)))
        return board


class Value1Ee(AbstractClueValue):
    id = Rule1Ee.id

    def __init__(self, pos: Position, count: int = 0, *args: object, **kwargs: object):
        super().__init__(pos, *args, **kwargs)
        self.count = count
        self.pos = pos
        self.value = SingleIntValue(count)

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)
        if not is_value_template(_data):
            raise TypeError("value is not template")
        value = SingleIntValue.try_from(_data)
        if value is None:
            raise ValueError("value is empty")
        return cls(pos, count=value.value)

    def __repr__(self) -> str:
        return str(self.count)

    def high_light(self, board: 'Board') -> List['Position'] | None:
        cells = _vertical_span(board, self.pos)
        cells |= _row_span(board, _up_path(board, self.pos))
        cells |= _row_span(board, _down_path(board, self.pos))
        return list(cells)

    def create_constraints(self, board: 'Board', switch: Switch):
        model = board.get_model()
        s = switch.get(model, self)
        pos = self.pos
        r0, c0 = pos.row, pos.col
        key = pos.board_key
        bound = board.boundary(key)
        rows = bound.row + 1
        cols = bound.col + 1

        def get_var(r: int, c: int):
            p = board.get_pos(r, c, key)
            if p is None:
                return None
            return board.get_variable(p)

        def make_and(var_list: List[IntVar], tag: str) -> IntVar:
            c = model.new_bool_var(f"1Ee_and_{tag}")
            if not var_list:
                model.add(c == 1).only_enforce_if(s)
                return c
            model.add_bool_and(var_list).only_enforce_if([c, s])
            model.add_bool_or([v.Not() for v in var_list] + [c]).only_enforce_if(s)
            return c

        def make_or(var_list: List[IntVar], tag: str) -> IntVar:
            c = model.new_bool_var(f"1Ee_or_{tag}")
            if not var_list:
                model.add(c == 0).only_enforce_if(s)
                return c
            model.add_bool_or(var_list).only_enforce_if([c, s])
            for v in var_list:
                model.add(c == 1).only_enforce_if([v, s])
            return c

        union_list: List[IntVar] = []
        tag_base = f"{r0}_{c0}"

        for qr in range(rows):
            for qc in range(cols):
                p = board.get_pos(qr, qc, key)
                if p is None:
                    continue
                tag = f"{tag_base}_{qr}_{qc}"

                # ---------- 竖直视野 V ----------
                if qr == r0 and qc == c0:
                    vhit = model.new_bool_var(f"1Ee_v_{tag}")
                    model.add(vhit == 1).only_enforce_if(s)
                elif qc != c0:
                    vhit = model.new_bool_var(f"1Ee_v_{tag}")
                    model.add(vhit == 0).only_enforce_if(s)
                else:
                    vs: List[IntVar] = []
                    ok = True
                    rs = range(qr, r0) if qr < r0 else range(r0 + 1, qr + 1)
                    for rr in rs:
                        gv = get_var(rr, c0)
                        if gv is None:
                            ok = False
                            break
                        vs.append(gv.Not())
                    if not ok:
                        vhit = model.new_bool_var(f"1Ee_v_{tag}")
                        model.add(vhit == 0).only_enforce_if(s)
                    else:
                        vhit = make_and(vs, f"v_{tag}")

                # ---------- 上方向远视野 U ----------
                u_terms: List[IntVar] = []
                if qr <= r0:
                    s_row = qr
                    cond_vars: List[IntVar] = []
                    ok = True
                    for rr in range(s_row, r0):
                        gv = get_var(rr, c0)
                        if gv is None:
                            ok = False
                            break
                        cond_vars.append(gv.Not())
                    if ok and s_row > 0:
                        gv = get_var(s_row - 1, c0)
                        if gv is None:
                            ok = False
                        else:
                            cond_vars.append(gv)
                    if ok:
                        cond = make_and(cond_vars, f"upcond_{tag}")
                        if qc == c0:
                            u_terms.append(cond)
                        else:
                            link_vars: List[IntVar] = []
                            ok2 = True
                            for cc in range(min(qc, c0), max(qc, c0) + 1):
                                gv = get_var(s_row, cc)
                                if gv is None:
                                    ok2 = False
                                    break
                                link_vars.append(gv.Not())
                            if ok2:
                                link = make_and(link_vars, f"uplink_{tag}")
                                comb = model.new_bool_var(f"1Ee_uc_{tag}")
                                model.add_bool_and([cond, link]).only_enforce_if([comb, s])
                                model.add_bool_or([cond.Not(), link.Not(), comb]).only_enforce_if(s)
                                u_terms.append(comb)
                uhit = make_or(u_terms, f"u_{tag}")

                # ---------- 下方向远视野 D ----------
                d_terms: List[IntVar] = []
                if qr >= r0:
                    s_row = qr
                    cond_vars = []
                    ok = True
                    for rr in range(r0 + 1, s_row + 1):
                        gv = get_var(rr, c0)
                        if gv is None:
                            ok = False
                            break
                        cond_vars.append(gv.Not())
                    if ok and s_row < rows - 1:
                        gv = get_var(s_row + 1, c0)
                        if gv is None:
                            ok = False
                        else:
                            cond_vars.append(gv)
                    if ok:
                        cond = make_and(cond_vars, f"downcond_{tag}")
                        if qc == c0:
                            d_terms.append(cond)
                        else:
                            link_vars = []
                            ok2 = True
                            for cc in range(min(qc, c0), max(qc, c0) + 1):
                                gv = get_var(s_row, cc)
                                if gv is None:
                                    ok2 = False
                                    break
                                link_vars.append(gv.Not())
                            if ok2:
                                link = make_and(link_vars, f"downlink_{tag}")
                                comb = model.new_bool_var(f"1Ee_dc_{tag}")
                                model.add_bool_and([cond, link]).only_enforce_if([comb, s])
                                model.add_bool_or([cond.Not(), link.Not(), comb]).only_enforce_if(s)
                                d_terms.append(comb)
                dhit = make_or(d_terms, f"d_{tag}")

                union = model.new_bool_var(f"1Ee_un_{tag}")
                model.add(union >= vhit).only_enforce_if(s)
                model.add(union >= uhit).only_enforce_if(s)
                model.add(union >= dhit).only_enforce_if(s)
                model.add(union <= vhit + uhit + dhit).only_enforce_if(s)
                union_list.append(union)

        model.add(sum(union_list) == self.count).only_enforce_if(s)
        get_logger().trace(f"[1Eエ] Value[{self.pos}: {self.count}] constraint added")
