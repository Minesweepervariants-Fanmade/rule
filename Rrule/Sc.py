#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026-04-16 16:17:52
# @Author  : NT (2201963934)
# @FileName: Sc.py
"""
[Sc] 连接 (Connection): 线索表示能连接周围八格内所有雷的连续路径所需额外添加的最小雷数，
路径可以经过不在周围八格中的雷。连通方式为四连通。
"""

from __future__ import annotations

from itertools import combinations, product
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, Set, Tuple

from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position, JSONObject
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template

if TYPE_CHECKING:
    from ortools.sat.python.cp_model import IntVar


# 以线索格为中心的八个方向，顺时针排列。
_RING_OFFSETS: Tuple[Tuple[int, int], ...] = (
    (-1, -1), (-1, 0), (-1, 1), (0, 1),
    (1, 1), (1, 0), (1, -1), (0, -1),
)

# 四连通方向。
_ADJ_OFFSETS: Tuple[Tuple[int, int], ...] = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _ring_positions(board: Board, pos: Position) -> List[Position]:
    """返回线索周围八格中有效的位置。"""
    result: List[Position] = []
    for dr, dc in _RING_OFFSETS:
        nxt = Position(pos.col + dc, pos.row + dr, pos.board_key)
        if board.is_valid(nxt):
            result.append(nxt)
    return result


def _neighbors4(board: Board, pos: Position) -> List[Position]:
    result: List[Position] = []
    for dr, dc in _ADJ_OFFSETS:
        nxt = Position(pos.col + dc, pos.row + dr, pos.board_key)
        if board.is_valid(nxt):
            result.append(nxt)
    return result


_INF = 10 ** 9
_LOCAL_INF = 10 ** 6


def _steiner_min(
    board: Board,
    cells: Sequence[Position],
    mines: Set[Position],
    targets: Sequence[Position],
) -> int:
    """节点带权 Steiner 树：已有雷代价 0，非雷格代价 1。

    返回连接全部 targets 所需的最小额外雷数；不连通时返回 _INF。
    """
    if len(targets) <= 1:
        return 0

    index = {pos: i for i, pos in enumerate(cells)}
    if any(target not in index for target in targets):
        return _INF

    n = len(cells)
    adjacency: List[List[int]] = [[] for _ in range(n)]
    for pos in cells:
        i = index[pos]
        for nxt in _neighbors4(board, pos):
            j = index.get(nxt)
            if j is not None:
                adjacency[i].append(j)

    cost = [0 if pos in mines else 1 for pos in cells]
    target_count = len(targets)
    full_mask = (1 << target_count) - 1

    # dp[mask][v]：包含终端集合 mask 且包含 v 的连通子树最小代价。
    dp: List[List[int]] = [[_INF] * n for _ in range(1 << target_count)]
    for i, target in enumerate(targets):
        dp[1 << i][index[target]] = 0

    import heapq

    for mask in range(1, 1 << target_count):
        # 合并两个子树。
        sub = (mask - 1) & mask
        while sub:
            other = mask ^ sub
            if sub < other:
                row_a = dp[sub]
                row_b = dp[other]
                row = dp[mask]
                for v in range(n):
                    val = row_a[v] + row_b[v] - cost[v]
                    if val < row[v]:
                        row[v] = val
            sub = (sub - 1) & mask

        # 节点带权最短路松弛。
        pq = [(dp[mask][v], v) for v in range(n) if dp[mask][v] < _INF]
        heapq.heapify(pq)
        row = dp[mask]
        while pq:
            dist, v = heapq.heappop(pq)
            if dist != row[v]:
                continue
            for nxt in adjacency[v]:
                nd = dist + cost[nxt]
                if nd < row[nxt]:
                    row[nxt] = nd
                    heapq.heappush(pq, (nd, nxt))

    return min(dp[full_mask])


def _local_min(
    board: Board,
    clue_pos: Position,
    ring: Sequence[Position],
    mines: Set[Position],
) -> int:
    """在 3x3 局部区域内计算连接周围雷所需的最小额外雷数（四连通）。

    掩码可能让局部区域不连通；此时返回 _LOCAL_INF。
    """
    targets = [pos for pos in ring if pos in mines]
    if len(targets) <= 1:
        return 0

    local_cells: List[Position] = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            pos = Position(clue_pos.col + dc, clue_pos.row + dr, clue_pos.board_key)
            if board.is_valid(pos):
                local_cells.append(pos)

    local_mines = {pos for pos in local_cells if pos in mines}
    value = _steiner_min(board, local_cells, local_mines, targets)
    return _LOCAL_INF if value >= _INF else value


def _min_extra_mines(board: Board, clue_pos: Position) -> int:
    """计算连接线索周围八格内所有雷所需额外添加的最小雷数。

    额外雷可以添加在任意非雷格上；已有的雷（包括八格之外的雷）免费作为路径。
    """
    targets = [
        pos for pos in _ring_positions(board, clue_pos)
        if board.get_type(pos, special='raw') == 'F'
    ]
    if len(targets) <= 1:
        return 0

    cells = [pos for pos, _ in board(key=clue_pos.board_key)]
    mines: Set[Position] = {
        pos for pos, _ in board("F", key=clue_pos.board_key, special='raw')
    }
    value = _steiner_min(board, cells, mines, targets)
    return len(cells) + 1 if value >= _INF else value


class RuleSc(AbstractClueRule):
    id = "Sc"
    name = "Connection"
    name.zh_CN = "连接"
    doc = (
        "Clue shows the minimum number of additional mines needed to connect all "
        "mines in the surrounding eight cells by a continuous 4-connected path; "
        "the path may use existing mines outside the eight cells."
    )
    doc.zh_CN = (
        "线索表示能连接周围八格内所有雷的连续路径所需额外添加的最小雷数，"
        "路径可以经过不在周围八格中的雷。连通方式为四连通。"
    )
    author = ("NT", 2201963934)
    tags = ["Creative", "Local", "Number Clue", "Connectivity"]
    creation_time = "2026-04-16 16:17:52"

    def fill(self, board: 'Board') -> 'Board':
        for pos, _ in board("N", special='raw'):
            board.set_value(pos, ValueSc(pos, value=_min_extra_mines(board, pos)))
        return board

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        # 每条线索的约束由 ValueSc.create_constraints 负责。
        model = board.get_model()
        _ = switch.get(model, self)


class ValueSc(AbstractClueValue):
    id = RuleSc.id

    def __init__(self, pos: Position, value: int = 0) -> None:
        super().__init__(pos, b'')
        self.value: SingleIntValue = SingleIntValue(int(value))

    @classmethod
    def from_json(cls, pos: Position, data: JSONObject) -> AbstractValue:
        _data = deep_unwrap(data)
        if not is_value_template(_data):
            raise TypeError("value is not a value template")
        value = SingleIntValue.try_from(_data)
        if value is None:
            raise ValueError("value is empty")
        return cls(pos, int(value.value))

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self.pos)
        need = int(self.value.value)

        ring: List[Position] = []
        ring_vars: List['IntVar'] = []
        for pos in _ring_positions(board, self.pos):
            var = board.get_variable(pos, special='raw')
            if var is not None:
                ring.append(pos)
                ring_vars.append(var)

        if not ring or not ring_vars:
            if need != 0:
                model.add_bool_or([]).only_enforce_if(s)
            return

        cells: List[Position] = [pos for pos, _ in board(key=self.pos.board_key)]
        mine_vars: Dict[Position, 'IntVar'] = {}
        for pos in cells:
            var = board.get_variable(pos, special='raw')
            if var is not None:
                mine_vars[pos] = var

        if not mine_vars:
            if need != 0:
                model.add_bool_or([]).only_enforce_if(s)
            return

        def add_cut_not_connected_instance(
            *,
            extra_cells: Tuple[Position, ...] = (),
            relax_literals: Tuple['IntVar', ...] = (),
            tag: str,
        ) -> None:
            """用“割”精确编码“不是所有周围雷都连通”。

            取 root 所在连通分量为 1 侧，其余为 0 侧；
            allowed 边两侧必须同侧。若要求至少一个周围雷在 0 侧，
            当且仅当 allowed 图不连通时可行。
            """
            extra_set = set(extra_cells)
            side: Dict[Position, 'IntVar'] = {
                pos: model.new_bool_var(
                    f"Sc_{tag}_side_{self.pos.col}_{self.pos.row}_{pos.col}_{pos.row}"
                )
                for pos in cells
            }
            root: Dict[Position, 'IntVar'] = {
                pos: model.new_bool_var(
                    f"Sc_{tag}_root_{self.pos.col}_{self.pos.row}_{pos.col}_{pos.row}"
                )
                for pos in ring
            }
            has_target = model.new_bool_var(
                f"Sc_{tag}_has_target_{self.pos.col}_{self.pos.row}"
            )
            model.add_max_equality(has_target, ring_vars).only_enforce_if(s)
            model.add(sum(root.values()) == has_target).only_enforce_if(s)
            for pos in ring:
                model.add(root[pos] <= mine_vars[pos]).only_enforce_if(s)
                model.add(side[pos] == 1).only_enforce_if(root[pos], s)

            # 只检查每条无向边一次。
            for pos in cells:
                for nxt in _neighbors4(board, pos):
                    if (pos.row, pos.col) >= (nxt.row, nxt.col):
                        continue
                    enforce: List['IntVar'] = []
                    if pos not in extra_set:
                        enforce.append(mine_vars[pos])
                    if nxt not in extra_set:
                        enforce.append(mine_vars[nxt])
                    if enforce:
                        model.add(side[pos] == side[nxt]).only_enforce_if(
                            *enforce, s
                        )
                    else:
                        model.add(side[pos] == side[nxt]).only_enforce_if(s)

            bad: List['IntVar'] = []
            for pos in ring:
                b = model.new_bool_var(
                    f"Sc_{tag}_bad_{self.pos.col}_{self.pos.row}_{pos.col}_{pos.row}"
                )
                model.add(b <= mine_vars[pos]).only_enforce_if(s)
                model.add(b + side[pos] <= 1).only_enforce_if(s)
                model.add(b >= mine_vars[pos] - side[pos]).only_enforce_if(s)
                bad.append(b)
            model.add_bool_or(list(bad) + list(relax_literals)).only_enforce_if(s)

        def add_flow_instance(
            *,
            use_vars: Optional[Dict[Position, 'IntVar']],
            gate: 'IntVar',
            tag: str,
        ) -> 'IntVar':
            """用单商品流精确编码“所有周围雷通过 allowed 格四连通”。

            根从周围雷中选一个；根向其余每个周围雷各送 1 单位流。
            流只能经过 allowed 格，因此目标全部可达等价于目标全部连通。
            """
            root: Dict[Position, 'IntVar'] = {
                pos: model.new_bool_var(
                    f"Sc_{tag}_root_{self.pos.col}_{self.pos.row}_{pos.col}_{pos.row}"
                )
                for pos in ring
            }
            has_target = model.new_bool_var(
                f"Sc_{tag}_has_target_{self.pos.col}_{self.pos.row}"
            )
            model.add_max_equality(has_target, ring_vars).only_enforce_if(s)
            model.add(sum(root.values()) == has_target).only_enforce_if(s)
            for pos in ring:
                model.add(root[pos] <= mine_vars[pos]).only_enforce_if(s)

            target_count = model.new_int_var(
                0, len(ring),
                f"Sc_{tag}_target_count_{self.pos.col}_{self.pos.row}",
            )
            model.add(
                target_count == sum(mine_vars[pos] for pos in ring)
            ).only_enforce_if(s)

            allowed: Dict[Position, object] = {}
            for pos in cells:
                if use_vars is not None:
                    allowed[pos] = mine_vars[pos] + use_vars[pos]
                else:
                    allowed[pos] = mine_vars[pos]

            # 根发出的流量为 (目标数 - 1)，每个非根目标吸收 1。
            supply: Dict[Position, object] = {pos: 0 for pos in cells}
            for pos in ring:
                root_times_count = model.new_int_var(
                    0, len(ring),
                    f"Sc_{tag}_root_count_{self.pos.col}_{self.pos.row}_{pos.col}_{pos.row}",
                )
                model.add_multiplication_equality(
                    root_times_count, [root[pos], target_count]
                ).only_enforce_if(s)
                supply[pos] = root_times_count - mine_vars[pos]

            flow: Dict[Tuple[Position, Position], 'IntVar'] = {}
            for pos in cells:
                for nxt in _neighbors4(board, pos):
                    f = model.new_int_var(
                        0, len(ring),
                        f"Sc_{tag}_flow_{self.pos.col}_{self.pos.row}_{pos.col}_{pos.row}_{nxt.col}_{nxt.row}",
                    )
                    flow[pos, nxt] = f
                    model.add(f <= len(ring) * allowed[pos]).only_enforce_if(gate, s)
                    model.add(f <= len(ring) * allowed[nxt]).only_enforce_if(gate, s)

            for pos in cells:
                neigh = _neighbors4(board, pos)
                out_flow = sum(flow[pos, nxt] for nxt in neigh)
                in_flow = sum(flow[nxt, pos] for nxt in neigh)
                model.add(out_flow - in_flow == supply[pos]).only_enforce_if(gate, s)

            return has_target

        def add_steiner_lower_bound(*, need: int, tag: str) -> None:
            """用 Dreyfus-Wagner 精确编码“全局最小额外雷数 >= need”。

            对所有周围雷子集计算节点带权 Steiner 树的最小代价，
            再按实际雷子集选出对应代价，要求其 >= need。
            """
            r = len(ring)
            mask_count = 1 << r
            n = len(cells)
            inf = n + 1
            index = {pos: i for i, pos in enumerate(cells)}
            cost = [1 - mine_vars[pos] for pos in cells]
            adjacency = [
                [index[nxt] for nxt in _neighbors4(board, pos)]
                for pos in cells
            ]

            dp: List[List['IntVar']] = [
                [
                    model.new_int_var(
                        0, inf,
                        f"Sc_{tag}_dp_{self.pos.col}_{self.pos.row}_{mask}_{v}",
                    )
                    for v in range(n)
                ]
                for mask in range(mask_count)
            ]
            for i, target in enumerate(ring):
                # 单终端初始化：雷终端代价 0，非雷环位置不会被实际 mask 选中，
                # 但仍给它节点代价 1，避免未使用 mask 中出现负代价导致模型无解。
                model.add(
                    dp[1 << i][index[target]] == cost[index[target]]
                ).only_enforce_if(s)

            for mask in range(1, mask_count):
                is_single = (mask & (mask - 1)) == 0
                single_source = (
                    index[ring[mask.bit_length() - 1]] if is_single else -1
                )
                for v in range(n):
                    # 单终端 mask 的源点距离固定为 cost(source)，不能再参与
                    # “等于邻居最小值”的方程，否则会被迫通过一个环回到自身。
                    if is_single and v == single_source:
                        continue
                    candidates: List[object] = [inf]
                    sub = (mask - 1) & mask
                    while sub:
                        other = mask ^ sub
                        if sub < other:
                            candidates.append(
                                dp[sub][v] + dp[other][v] - cost[v]
                            )
                        sub = (sub - 1) & mask
                    for u in adjacency[v]:
                        candidates.append(dp[mask][u] + cost[v])
                    model.add_min_equality(
                        dp[mask][v], candidates
                    ).only_enforce_if(s)

            best: List['IntVar'] = [
                model.new_int_var(
                    0, inf,
                    f"Sc_{tag}_best_{self.pos.col}_{self.pos.row}_{mask}",
                )
                for mask in range(mask_count)
            ]
            model.add(best[0] == 0).only_enforce_if(s)
            for mask in range(1, mask_count):
                model.add_min_equality(best[mask], dp[mask]).only_enforce_if(s)

            mask_index = model.new_int_var(
                0, mask_count - 1,
                f"Sc_{tag}_mask_{self.pos.col}_{self.pos.row}",
            )
            model.add(
                mask_index
                == sum(
                    mine_vars[pos] * (1 << i)
                    for i, pos in enumerate(ring)
                )
            ).only_enforce_if(s)
            min_cost = model.new_int_var(
                0, inf,
                f"Sc_{tag}_min_cost_{self.pos.col}_{self.pos.row}",
            )
            model.add_element(mask_index, best, min_cost).only_enforce_if(s)
            model.add(min_cost >= need).only_enforce_if(s)

        # 局部 3x3 最优值 L 不小于全局最优值。
        # 若 L == need，则全局最优值必然 <= need，不需要再启动全局流约束；
        # 只有 L > need 时才由流约束确认“全局确实可用 <= need 个额外雷连通”。
        flow_flag = model.new_bool_var(
            f"Sc_need_flow_{self.pos.col}_{self.pos.row}"
        )
        allowed_rows: List[Tuple[int, ...]] = []
        for bits in product((0, 1), repeat=len(ring)):
            mines = {pos for pos, bit in zip(ring, bits) if bit}
            local_value = _local_min(board, self.pos, ring, mines)
            if local_value >= need:
                allowed_rows.append(tuple(bits) + (1 if local_value > need else 0,))
        if allowed_rows:
            model.add_allowed_assignments(
                ring_vars + [flow_flag], allowed_rows
            ).only_enforce_if(s)
        else:
            # 局部最优值已经小于 need，该线索值不可能成立。
            model.add_bool_or([]).only_enforce_if(s)
            return

        if need == 0:
            # 不允许添加额外雷，只要求周围雷通过已有雷连通。
            add_flow_instance(use_vars=None, gate=flow_flag, tag="conn0")
            return

        # 上界：存在一种不超过 need 个额外雷的连接方案。
        use_vars: Dict[Position, 'IntVar'] = {}
        for pos in cells:
            use = model.new_bool_var(
                f"Sc_use_{self.pos.col}_{self.pos.row}_{pos.col}_{pos.row}"
            )
            use_vars[pos] = use
            # 只能在非雷格上添加。
            model.add(use + mine_vars[pos] <= 1).only_enforce_if(flow_flag, s)
        model.add(sum(use_vars.values()) <= need).only_enforce_if(flow_flag, s)
        has_target = add_flow_instance(
            use_vars=use_vars, gate=flow_flag, tag="upper"
        )
        model.add(has_target == 1).only_enforce_if(s)

        if need > 3:
            # need 大于 3 时，使用通用 Steiner 树下界，精确覆盖任意雷数。
            if len(ring) >= 2:
                add_steiner_lower_bound(need=need, tag="lower_steiner")
            return

        # 下界：禁止 0 个额外雷连通。
        add_cut_not_connected_instance(tag="lower0")

        # 下界：禁止 1 个额外雷连通。
        if need >= 2:
            for pos in cells:
                add_cut_not_connected_instance(
                    extra_cells=(pos,),
                    relax_literals=(mine_vars[pos],),
                    tag=f"lower1_{pos.col}_{pos.row}",
                )

        # 下界：禁止 2 个额外雷连通。
        if need >= 3:
            for pos_a, pos_b in combinations(cells, 2):
                add_cut_not_connected_instance(
                    extra_cells=(pos_a, pos_b),
                    relax_literals=(mine_vars[pos_a], mine_vars[pos_b]),
                    tag=f"lower2_{pos_a.col}_{pos_a.row}_{pos_b.col}_{pos_b.row}",
                )


