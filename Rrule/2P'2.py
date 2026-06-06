#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/03/01 13:28:35
# @Author  : \u6ce2\u5e38\u672a\u6765 (81500378)
# @FileName: 2P'2_81500378.py
"""
[2P'2] 线索数字表示最近的两个雷的曼哈顿距离乘积
作者: \u6ce2\u5e38\u672a\u6765 (81500378)
"""

from typing import Dict, List, Tuple

from ortools.sat.python.cp_model import IntVar

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position
from ....utils.tool import get_logger


def manhattan_neighbors(pos: Position, distance: int) -> List[Position]:
    """返回曼哈顿距离恰好等于 distance 的所有有效格子"""
    neighbors = []
    for dx in range(distance + 1):
        dy = distance - dx
        if dx == 0:
            if dy == 0:
                continue
            # 左/右
            left = pos.left(dy)
            right = pos.right(dy)
            if left is not None:
                neighbors.append(left)
            if right is not None:
                neighbors.append(right)
        elif dy == 0:
            up = pos.up(dx)
            down = pos.down(dx)
            if up is not None:
                neighbors.append(up)
            if down is not None:
                neighbors.append(down)
        else:
            # 四个对角方向的组合
            up_left = pos.up(dx).left(dy)
            up_right = pos.up(dx).right(dy)
            down_left = pos.down(dx).left(dy)
            down_right = pos.down(dx).right(dy)
            for p in (up_left, up_right, down_left, down_right):
                if p is not None:
                    neighbors.append(p)
    return neighbors


class Rule2P2(AbstractClueRule):
    id = "2P'2"
    name = "Manhattan Product"
    name.zh_CN = "曼哈顿乘积"
    doc = "Clue value is the product of Manhattan distances to the two nearest mines"
    doc.zh_CN = "线索数字表示最近的两个雷的曼哈顿距离乘积"
    author = ("\u6ce2\u5e38\u672a\u6765", 81500378)
    tags = ["Creative", "Local", "Number Clue", "Extensive Trial"]
    creation_time = "2026-03-01"

    @classmethod
    def get_factor_pairs(cls, n: int) -> List[Tuple[int, int]]:
        """返回所有形如 (a,b) 的正整数对，满足 a ≤ b 且 a * b = n"""
        pairs = []
        for a in range(1, int(n ** 0.5) + 1):
            if n % a == 0:
                b = n // a
                pairs.append((a, b))
        return pairs

    def fill(self, board: Board) -> Board:
        """根据答案板填充所有非雷格的线索值"""
        mines = [pos for pos, _ in board("F", special='raw')]
        if len(mines) < 2:
            # 不足两个雷时，所有非雷格线索值设为 0（或其它约定）
            for pos, _ in board("N"):
                board.set_value(pos, Value2P2(pos, code=bytes([0])))
            return board

        # 预先计算每个格子的曼哈顿距离到所有雷
        for pos, _ in board("N"):
            dists = []
            for m in mines:
                d = abs(pos.x - m.x) + abs(pos.y - m.y)
                dists.append(d)
            dists.sort()
            product = dists[0] * dists[1]
            board.set_value(pos, Value2P2(pos, code=product.to_bytes(2, 'big')))
        return board

    def create_constraints(self, board: Board, switch):
        """为每个 Value2P2 线索添加约束"""
        # 这个规则没有全局约束，单个线索的约束统一在 Value2P2 中实现
        pass


class Value2P2(AbstractClueValue):
    id = "2P2"
    def __init__(self, pos: Position, code: bytes = None):
        super().__init__(pos, code)
        if code is None:
            self.value = 0
        else:
            # 支持 1 字节或 2 字节编码（产品最大可能值通常 ≤ 255，但留出扩展）
            if len(code) == 1:
                self.value = code[0]
            else:
                self.value = int.from_bytes(code[:2], 'big')
        self.pos = pos

    def __repr__(self) -> str:
        return str(self.value)

    def code(self) -> bytes:
        return self.value.to_bytes(2, 'big')

    @classmethod
    def type(cls) -> bytes:
        return Rule2P2.id.encode('ascii')

    def high_light(self, board: Board) -> List[Position]:
        # 高亮距离最近的两个雷所在的环（用于前端展示）
        if self.value == 0:
            return []
        # 简单实现：返回所有与当前格曼哈顿距离不超过 max(a,b) 的格子
        # 更精确的高亮可以参考 2P 的做法，但这里仅用于提示，可以粗略显示
        max_dist = int(self.value ** 0.5) + 1
        highlights = []
        for d in range(1, max_dist + 1):
            highlights.extend(manhattan_neighbors(self.pos, d))
        return highlights

    def create_constraints(self, board: Board, switch):
        """
        编码约束：当前线索格周围雷的曼哈顿距离中，最小的两个距离之乘积等于 self.value。
        使用“候选距离对”枚举法，对每一对 (a,b) 满足 a*b == value 且 a≤b，建立如下约束：
        - 若 a < b :
            - 距离 a 的环上至少有一个雷
            - 距离 b 的环上至少有一个雷
            - 距离 < a 的环上没有雷
            - 距离在 (a, b) 之间的环上没有雷
        - 若 a == b :
            - 距离 a 的环上至少有 2 个雷
            - 距离 < a 的环上没有雷
        """
        model = board.get_model()
        s = switch.get(model, self)
        logger = get_logger()

        # 如果线索值为 0，直接禁用约束（意味着该格不存在两个雷）
        if self.value == 0:
            return

        # 获取棋盘的最大可能曼哈顿距离（从当前格出发）
        bound = board.boundary(self.pos.board_key)
        max_possible_dist = bound.x + bound.y + 1

        # 预先计算每个距离层上的变量列表
        layers: Dict[int, List[IntVar]] = {}
        for d in range(1, max_possible_dist + 1):
            cells = manhattan_neighbors(self.pos, d)
            # 筛选有效格子并获取变量
            vars_in_layer = []
            for cell in cells:
                if board.in_bounds(cell):
                    var = board.get_variable(cell, special='raw')
                    if var is not None:
                        vars_in_layer.append(var)
            if vars_in_layer:
                layers[d] = vars_in_layer

        # 枚举所有可能的因子对 (a,b) 且 a*b == self.value
        pairs = Rule2P2.get_factor_pairs(self.value)
        if not pairs:
            # 如果没有合法因子对，则约束不可满足
            model.Add(False).OnlyEnforceIf(s)
            return

        candidate_vars = []
        for a, b in pairs:
            # 确保距离 a、b 不超过最大可能距离
            if a > max_possible_dist or b > max_possible_dist:
                continue
            # 检查必要的层是否存在变量
            if a not in layers or (a != b and b not in layers):
                continue
            if a == b and len(layers[a]) < 2:
                continue

            # 为该候选对创建一个布尔开关变量
            cand = model.NewBoolVar(f"2P2_cand_{self.pos}_{a}_{b}")
            candidate_vars.append(cand)

            # 约束1: 排除距离 < a 的所有雷
            for d in range(1, a):
                if d in layers:
                    for var in layers[d]:
                        model.Add(var == 0).OnlyEnforceIf([cand, s])

            # 约束2: 处理 a 层
            if a == b:
                # 需要至少两个雷
                model.Add(sum(layers[a]) >= 2).OnlyEnforceIf([cand, s])
            else:
                model.Add(sum(layers[a]) >= 1).OnlyEnforceIf([cand, s])
                # 排除 a 与 b 之间的层
                for d in range(a + 1, b):
                    if d in layers:
                        for var in layers[d]:
                            model.Add(var == 0).OnlyEnforceIf([cand, s])
                # b 层也需要至少一个雷
                model.Add(sum(layers[b]) >= 1).OnlyEnforceIf([cand, s])

        if not candidate_vars:
            model.Add(False).OnlyEnforceIf(s)
            return

        # 至少有一个候选对成立
        model.AddBoolOr(candidate_vars).OnlyEnforceIf(s)
        logger.trace(f"[2P'2] {self.pos}: value={self.value}, candidates={len(candidate_vars)}")
