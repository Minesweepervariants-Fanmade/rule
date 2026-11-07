#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026-11-07
# @Author  : mabopei1 (81500378)
# @FileName: Star1Z^.py
"""
[*1Z^] 单行通道：线索为箭头线索。对于每一个线索，可以从该格箭头方向出发组成至少一条四连通非雷路径回到原点，且经过的所有箭头格都满足路径方向。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.board import Board, Position
from minesweepervariants.json_object import JSONObject, deep_unwrap
from minesweepervariants.utils.impl_obj import VALUE_QUESS
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template
from minesweepervariants.utils.image_template import get_col, get_dummy, get_image

if TYPE_CHECKING:
    from minesweepervariants.impl.summon.solver import Switch


# 0=上 1=右 2=下 3=左（四连通）
DIRECTION_OFFSETS = [(-1, 0), (0, 1), (1, 0), (0, -1)]
ARROW_CHARS = "↑→↓←"
ARROW_IMAGES = ["up", "right", "down", "left"]


def _neighbor(board: Board, pos: Position, dr: int, dc: int, key: str) -> Optional[Position]:
    """按行列偏移取相邻位置；越界返回 None（不使用会环绕的 board.get_pos）。"""
    q = Position(pos.col + dc, pos.row + dr, key)
    if not board.is_valid(q):
        return None
    return q


def _direction_to(pos: Position, nxt: Position) -> int:
    dr = nxt.row - pos.row
    dc = nxt.col - pos.col
    for d, (odr, odc) in enumerate(DIRECTION_OFFSETS):
        if dr == odr and dc == odc:
            return d
    raise ValueError(f"positions not adjacent: {pos} {nxt}")


def _find_path_avoiding(
    adj: Dict[Position, List[Position]],
    src: Position,
    dst: Position,
    forbidden: Set[Position],
) -> Optional[List[Position]]:
    """在无向图 adj 中找一条 src -> dst 的简单路径，禁止经过 forbidden 中的中间格。

    src 与 dst 本身可以在 forbidden 之外使用（调用方保证）。
    返回 [src, ..., dst]，找不到返回 None。
    """
    if src == dst:
        return [src]
    prev: Dict[Position, Optional[Position]] = {src: None}
    stack: List[Position] = [src]
    while stack:
        u = stack.pop()
        for v in adj[u]:
            if v != dst and v in forbidden:
                continue
            if v == dst:
                path = [u]
                cur: Optional[Position] = u
                while cur is not None and cur != src:
                    cur = prev[cur]
                    if cur is not None:
                        path.append(cur)
                path.reverse()
                path.append(dst)
                return path
            if v in prev:
                continue
            prev[v] = u
            stack.append(v)
    return None


def _find_cycle_avoiding(
    adj: Dict[Position, List[Position]],
    start: Position,
    forbidden: Set[Position],
) -> Optional[List[Position]]:
    """找一条经过 start 且不经过 forbidden 中任何格的简单环（长度为 2 允许）。

    返回环上按顺序的格子列表（不含重复的起点）。找不到返回 None。
    """
    if start in forbidden:
        return None
    for nb in adj[start]:
        if nb in forbidden:
            continue
        # 在 nb 到 start 之间找一条不经过 start（起点除外）的路径
        sub_forbidden = set(forbidden)
        # 从 nb 出发，找 nb -> start 的路径，中间不可经过 start
        prev: Dict[Position, Optional[Position]] = {nb: None}
        stack: List[Position] = [nb]
        found = False
        while stack:
            u = stack.pop()
            for v in adj[u]:
                if v in sub_forbidden:
                    continue
                if v == start:
                    # 找到路径 nb -> ... -> u -> start
                    path = [u]
                    cur: Optional[Position] = u
                    while cur is not None and cur != nb:
                        cur = prev[cur]
                        if cur is not None:
                            path.append(cur)
                    path.reverse()
                    # path = [nb, ..., u]
                    cycle = [start] + path
                    found = True
                    break
                if v in prev or v == start:
                    continue
                prev[v] = u
                stack.append(v)
            if found:
                break
        if found:
            # 去重：环中起点只出现一次
            result: List[Position] = []
            seen_local: Set[Position] = set()
            for p in cycle:
                if p in seen_local:
                    continue
                seen_local.add(p)
                result.append(p)
            if len(result) >= 2:
                return result
    return None


class RuleStar1ZHat(AbstractClueRule):
    """
    [*1Z^] 单行通道：箭头线索格沿箭头方向出发，存在一条四连通非雷路径回到原点。

    语义等价表述：
    - 题板每个非雷格要么是箭头线索格，要么是无箭头的问号格。
    - 存在一个以箭头格出边为约束的有向流：
        * 每条带正流量的边两端必须是非雷格；
        * 除箭头格强制流出 >= 1 外，所有格流量守恒（入 = 出）；
        * 箭头格只有一条出边（其箭头方向）。
    - 流量守恒 + 每箭头格流出即保证：每个箭头格都属于某个有向环，
      即从该格沿箭头方向出发能回到自身；环之间可共享无箭头格，
      无箭头格只作为中转（入 = 出）。
    """

    id = "*1Z^"
    name = "Single Path"
    name.zh_CN = "单行通道"
    doc = ("Clue is an arrow clue. For each clue, starting from that cell in its arrow direction, "
           "there must be at least one 4-connected non-mine path back to the origin, "
           "and all arrow cells passed must satisfy the path direction.")
    doc.zh_CN = "线索为箭头线索。对于每一个线索，可以从该格箭头方向出发组成至少一条四连通非雷路径回到原点，且经过的所有箭头格都满足路径方向。"
    author = ("mabopei1", 81500378)
    tags = ["Variant", "Global", "Connectivity", "Construction"]
    creation_time = "2026-11-06"

    # ------------------------------------------------------------------ fill
    def fill(self, board: Board) -> Board:
        for key in board.get_interactive_keys():
            non_mine: List[Position] = [
                pos for pos, _ in board(key=key)
                if board.get_type(pos, special="raw") != "F"
            ]
            if not non_mine:
                continue
            non_mine_set = set(non_mine)

            # 构建非雷格四连通无向邻接表
            adj: Dict[Position, List[Position]] = {p: [] for p in non_mine}
            for p in non_mine:
                for dr, dc in DIRECTION_OFFSETS:
                    q = _neighbor(board, p, dr, dc, key)
                    if q is None or q not in non_mine_set:
                        continue
                    adj[p].append(q)

            # 顶点不相交环打包：只在互不相交的环上赋箭头，其余问号。
            # 这样无论 #(sharp) 机制后续把哪些箭头格替换成 V 数字格，
            # 被破坏的环都退化为“以自由格为中转的回路”，流量始终守恒，保证可解。
            used: Set[Position] = set()
            for start in non_mine:
                if start in used:
                    continue
                cycle = _find_cycle_avoiding(adj, start, used)
                if cycle is None or len(cycle) < 2:
                    continue
                n_cycle = len(cycle)
                for i, u in enumerate(cycle):
                    v = cycle[(i + 1) % n_cycle]
                    board.set_value(u, ValueStar1ZHat(u, _direction_to(u, v)))
                    used.add(u)

            for p in non_mine:
                if p not in used:
                    board.set_value(p, VALUE_QUESS)

        return board

    # -------------------------------------------------------------- constraints
    def create_constraints(self, board: Board, switch: "Switch") -> None:
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            positions: List[Position] = [pos for pos, _ in board(key=key)]
            if not positions:
                continue
            pos_index = {pos: i for i, pos in enumerate(positions)}

            arrow_dir: Dict[Position, Optional[int]] = {pos: None for pos in positions}
            arrow_positions: List[Position] = []
            for pos, obj in board(key=key, mode="obj"):
                if isinstance(obj, ValueStar1ZHat):
                    arrow_dir[pos] = obj.direction
                    arrow_positions.append(pos)

            raw: Dict[Position, Optional[object]] = {
                pos: board.get_variable(pos, special="raw") for pos in positions
            }

            K = max(1, len(arrow_positions))

            out_edges: Dict[Position, List[object]] = {pos: [] for pos in positions}
            in_edges: Dict[Position, List[object]] = {pos: [] for pos in positions}

            edge_created: Set[Tuple[Position, Position]] = set()

            def add_edge(u: Position, v: Position) -> None:
                if (u, v) in edge_created:
                    return
                edge_created.add((u, v))
                e = model.new_int_var(
                    0, K, f"1Zhat_e_{key}_{pos_index[u]}_{pos_index[v]}"
                )
                out_edges[u].append(e)
                in_edges[v].append(e)

            for pos in positions:
                if raw[pos] is None:
                    continue
                d = arrow_dir.get(pos)
                if d is not None:
                    # 箭头格：只有一条出边，指向箭头方向
                    dr, dc = DIRECTION_OFFSETS[d]
                    npos = _neighbor(board, pos, dr, dc, key)
                    if npos is None or npos not in pos_index:
                        model.add(False).only_enforce_if(s)
                        continue
                    add_edge(pos, npos)
                else:
                    # 无箭头格：允许四个方向出边（仅限题板内）
                    for d2 in range(4):
                        dr, dc = DIRECTION_OFFSETS[d2]
                        npos = _neighbor(board, pos, dr, dc, key)
                        if npos is None or npos not in pos_index:
                            continue
                        add_edge(pos, npos)

            # 流量为正 => 两端都必须是非雷格
            for pos in positions:
                raw_i = raw[pos]
                if raw_i is None:
                    continue
                for e in out_edges[pos]:
                    model.add(e <= K * (1 - raw_i)).only_enforce_if(s)
                for e in in_edges[pos]:
                    model.add(e <= K * (1 - raw_i)).only_enforce_if(s)

            # 流量守恒：入 == 出
            for pos in positions:
                out_sum = sum(out_edges[pos]) if out_edges[pos] else 0
                in_sum = sum(in_edges[pos]) if in_edges[pos] else 0
                model.add(out_sum == in_sum).only_enforce_if(s)

            # 每个箭头格流出 >= 1
            for pos in arrow_positions:
                out_sum = sum(out_edges[pos]) if out_edges[pos] else 0
                model.add(out_sum >= 1).only_enforce_if(s)

    def suggest_total(self, info: dict) -> None:
        total_cells = 0
        for key in info["interactive"]:
            total_cells += info["total"][key]
        if total_cells > 0:
            info["soft_fn"](int(total_cells * 0.5), 0)


class ValueStar1ZHat(AbstractClueValue):
    id = RuleStar1ZHat.id

    def __init__(self, pos: Position, direction: int = 0):
        super().__init__(pos, b"")
        self.direction = int(direction) % 4
        self.value = SingleIntValue(self.direction)

    def __repr__(self) -> str:
        return ARROW_CHARS[self.direction]

    @classmethod
    def from_json(cls, pos: Position, data: JSONObject) -> AbstractValue:
        _data = deep_unwrap(data)
        if not is_value_template(_data):
            raise TypeError("value is not template")
        v = SingleIntValue.try_from(_data)
        if v is None:
            raise ValueError("value is empty")
        return cls(pos, v.value)

    def compose(self, board) -> dict:
        return get_col(
            get_dummy(height=0.175),
            get_image(ARROW_IMAGES[self.direction]),
            get_dummy(height=0.175),
        )

    def web_component(self, board) -> dict:
        from minesweepervariants.utils.web_template import Number
        return Number(ARROW_CHARS[self.direction])

    def tag(self, board) -> bytes:
        return b""

    def create_constraints(self, board, switch) -> None:
        # 约束统一在 RuleStar1ZHat.create_constraints 中构造
        pass
