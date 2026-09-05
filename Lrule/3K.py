#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026-09-05 21:10
# @Author  : NT (2201963934)
# @FileName: 3K.py
"""
[3K] 三消：题版可以经过若干轮三消变成全空题版。

规则语义：
- 每轮选中所有面积不小于 3 的雷/非雷连通块（四连通）。
- "删去"这些格子，让上面的格子落下来（每列独立垂直下落），并在上方补齐非雷格。
- 重复此操作若干轮后，若题版内没有雷格，则该题版满足规则。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Set, Tuple

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.position import Position

if TYPE_CHECKING:
    from minesweepervariants.impl.summon.solver import Switch


class Rule3K(AbstractMinesRule):
    """[3K] 三消规则：fill 阶段验证盘面是否可通过三消消空。"""

    id = "3K"
    name = "3K"
    name.zh_CN = "三消"
    doc = "The board can be cleared by repeatedly removing all 4-connected components of size >= 3 and applying gravity."
    doc.zh_CN = "题版可以经过若干轮三消（删除面积>=3的连通块并下落）变成全空题版。"
    tags = ["Creative", "Variant", "Construction"]
    creation_time = "2026-09-05"
    author = ("NT", 2201963934)

    def __init__(self, board: Board | None = None, data: str | None = None) -> None:
        super().__init__(board, data)

    def fill(self, board: Board) -> Board:
        """在已知完整答案板时，验证盘面是否可三消消空。

        Args:
            board: 已填充雷和线索的完整答案板。

        Returns:
            如果可消，返回原 board；否则抛出 ValueError 触发重试。
        """
        if not self._is_clearable(board):
            raise ValueError("[3K] 盘面无法通过三消消空，重新生成")
        return board

    def _is_clearable(self, board: Board) -> bool:
        """模拟三消过程，判断盘面是否可消空。"""
        # 获取主交互板尺寸
        keys = board.get_interactive_keys()
        if not keys:
            return False
        key = keys[0]
        bound = board.boundary(key)
        rows = bound.row + 1
        cols = bound.col + 1

        # 转换为布尔矩阵：True 表示雷，False 表示非雷
        grid = [[False] * cols for _ in range(rows)]
        for r in range(rows):
            for c in range(cols):
                pos = board.get_pos(r, c, key)
                if pos is None or not board.is_valid(pos):
                    continue
                grid[r][c] = (board.get_type(pos, special='raw') == 'F')

        # 模拟三消，最大轮数设为 100（足够大）
        for _ in range(100):
            # 1. 找所有四连通连通块及其面积
            visited = [[False] * cols for _ in range(rows)]
            components: List[Set[Tuple[int, int]]] = []

            for r in range(rows):
                for c in range(cols):
                    if visited[r][c]:
                        continue
                    # BFS 收集连通块
                    queue = [(r, c)]
                    visited[r][c] = True
                    comp = set()
                    while queue:
                        cr, cc = queue.pop()
                        comp.add((cr, cc))
                        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nr, nc = cr + dr, cc + dc
                            if 0 <= nr < rows and 0 <= nc < cols and not visited[nr][nc]:
                                # 连通条件：两个格子状态相同（都是雷或都是非雷）
                                if grid[nr][nc] == grid[cr][cc]:
                                    visited[nr][nc] = True
                                    queue.append((nr, nc))
                    if comp:
                        components.append(comp)

            # 2. 找出所有面积 >= 3 的连通块
            to_remove: Set[Tuple[int, int]] = set()
            for comp in components:
                if len(comp) >= 3:
                    to_remove.update(comp)

            # 3. 如果没有可删除的块，则停止
            if not to_remove:
                break

            # 4. 删除这些格子（标记为非雷），并应用重力
            for r, c in to_remove:
                grid[r][c] = False

            # 每列独立下落：从下往上，将非删除的格子往下压
            for c in range(cols):
                write_row = rows - 1
                for r in range(rows - 1, -1, -1):
                    if grid[r][c]:
                        # 如果是雷，保留
                        grid[write_row][c] = True
                        write_row -= 1
                # 上方剩余位置填充非雷
                for r in range(write_row, -1, -1):
                    grid[r][c] = False

        # 5. 检查是否还有雷
        for r in range(rows):
            for c in range(cols):
                if grid[r][c]:
                    return False
        return True

    def create_constraints(self, board: Board, switch: Switch) -> None:
        """不添加 CP 约束，仅作为生成期过滤器。"""
        # 为了满足框架要求，添加一个永真约束（总雷数 ≥ 0，始终成立）
        model = board.get_model()
        s = switch.get(model, self)
        # 这里不添加任何实质约束，因为可消性已在 fill 阶段验证。
        # 添加一个无害的约束：总雷数不大于总格子数（几乎永真，但避免空模型）。
        positions = list(board(mode="pos"))
        if positions:
            total_var = model.NewIntVar(0, len(positions), "3K_total")
            all_vars = [board.get_variable(pos, special='raw') for pos in positions]
            model.Add(total_var == sum(all_vars)).OnlyEnforceIf(s)
            # 这个约束总是满足，因为 total_var 范围已限制。

    def suggest_total(self, info: dict) -> None:
        """建议总雷数，使其处于合理范围（约 30%~50%）。"""
        ub = 0
        for key in info.get("interactive", []):
            total_cells = info.get("total", {}).get(key, 0)
            ub += total_cells
        if ub > 0:
            # 软约束：建议总雷数在 30%~50% 之间
            info["soft_fn"](int(ub * 0.35), 0)
            info["soft_fn"](int(ub * 0.45), 0)
