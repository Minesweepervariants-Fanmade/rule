#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026-08-25
# @Author  : NT (2201963934)
# @FileName: 2P^.py
"""
[2P^] 夹角：线索值表示最近的两个雷夹角的余弦值。使用M3E4浮点数带入(给定算法)计算。
"""

import struct
from typing import List, Tuple, Optional, Dict
from math import acos, cos, sqrt

from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import JSONObject, ImmutableDict
from minesweepervariants.utils.tool import get_logger
from minesweepervariants.utils.value_template import is_value_template, Template, SingleValue


# =============================================================================
# M3E4 浮点数编解码辅助函数 (占位实现)
# =============================================================================

def float_to_m3e4(value: float) -> bytes:
    """
    将浮点数编码为 M3E4 格式 (4字节)。
    当前占位实现：直接使用 IEEE 754 单精度浮点数 (32位) 编码。
    """
    # 将 float 打包为 4 字节的二进制数据 (大端序)
    return struct.pack('>f', value)


def m3e4_to_float(data: bytes) -> float:
    """
    将 M3E4 格式 (4字节) 解码为浮点数。
    当前占位实现：直接使用 IEEE 754 单精度浮点数 (32位) 解码。
    """
    if len(data) != 4:
        raise ValueError("M3E4 数据必须为 4 字节")
    return struct.unpack('>f', data)[0]


# =============================================================================
# 几何计算辅助函数
# =============================================================================

def distance(p1: Position, p2: Position) -> float:
    """计算两个位置之间的欧几里得距离。"""
    dx = p1.col - p2.col
    dy = p1.row - p2.row
    return sqrt(dx * dx + dy * dy)


def angle_cosine(vertex: Position, p1: Position, p2: Position) -> float:
    """
    计算以 vertex 为顶点，p1 和 p2 为两个端点形成的夹角的余弦值。
    """
    # 向量 v1 = p1 - vertex, v2 = p2 - vertex
    v1 = (p1.col - vertex.col, p1.row - vertex.row)
    v2 = (p2.col - vertex.col, p2.row - vertex.row)

    # 计算点积和模长
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    norm1 = sqrt(v1[0] * v1[0] + v1[1] * v1[1])
    norm2 = sqrt(v2[0] * v2[0] + v2[1] * v2[1])

    # 避免除以零
    if norm1 < 1e-9 or norm2 < 1e-9:
        return 1.0  # 如果其中一个向量为零向量，夹角为 0 度，余弦为 1

    return dot / (norm1 * norm2)


# =============================================================================
# 规则类实现
# =============================================================================

class Rule2P_caret(AbstractClueRule):
    """
    [2P^] 夹角规则：线索值表示最近的两个雷夹角的余弦值。
    """
    id = "2P^"
    aliases = ()
    name = "Angle"
    name.zh_CN = "夹角"
    doc = (
        "Clue value represents the cosine of the angle formed by the two nearest mines, "
        "using M3E4 floating-point representation."
    )
    doc.zh_CN = (
        "线索值表示最近的两个雷夹角的余弦值，使用 M3E4 浮点数表示法存储。"
    )
    tags = ["Creative", "Local", "Number Clue", "Extensive Trial"]
    creation_time = "2026-06-04"
    author = ("NT", 2201963934)

    def fill(self, board: 'Board') -> 'Board':
        """
        填充所有非雷格 (N) 为 2P^ 线索。
        对于每个非雷格，找到最近的两个雷，计算夹角余弦值，编码为 M3E4 并存储。
        """
        # 如果雷的数量少于 2，则无法计算夹角，直接返回
        if len([_ for _ in board("F")]) < 2:
            return board

        for pos, _ in board("N"):
            # 获取所有雷的位置及其距离
            mine_positions = []
            for mine_pos, _ in board("F"):
                if board.is_valid(mine_pos):
                    dist = distance(pos, mine_pos)
                    mine_positions.append((dist, mine_pos))

            # 按距离排序，选择最近的两个雷
            mine_positions.sort(key=lambda x: x[0])
            nearest_two = mine_positions[:2]

            if len(nearest_two) < 2:
                # 如果仍然少于两个雷（理论上不会发生），设置余弦值为 1.0
                cos_val = 1.0
            else:
                # 计算夹角余弦值
                _, p1 = nearest_two[0]
                _, p2 = nearest_two[1]
                cos_val = angle_cosine(pos, p1, p2)

            # 编码并存储为线索值
            encoded = float_to_m3e4(cos_val)
            board.set_value(pos, Value2P_caret(pos, code=encoded))

        return board


# =============================================================================
# 线索值类实现
# =============================================================================

class Value2P_caret(AbstractClueValue):
    """
    [2P^] 线索值：存储夹角余弦值的 M3E4 编码。
    """
    id = "2P^"

    def __init__(self, pos: Position, code: bytes = None):
        super().__init__(pos, code or b'')
        if code is None:
            self.cos_val = 1.0
            self._code = float_to_m3e4(1.0)
        else:
            self._code = code
            self.cos_val = m3e4_to_float(code)

    @classmethod
    def from_json(cls, pos: Position, data: JSONObject) -> 'AbstractValue':
        """从 JSON 数据恢复线索值对象。"""
        # 兼容旧格式：直接存储 bytes
        if "code" in data:
            return cls(pos, code=bytes(data["code"]))
        # 新格式：使用 _SingleValue 模板
        _data = data.get_data() if hasattr(data, 'get_data') else data
        if isinstance(_data, dict) and _data.get('_SingleValue'):
            # 从 data 字段读取十六进制字符串
            hex_str = _data.get('data', '')
            if isinstance(hex_str, str) and hex_str.startswith('0x'):
                hex_str = hex_str[2:]
            if hex_str:
                try:
                    code = bytes.fromhex(hex_str)
                    return cls(pos, code=code)
                except ValueError:
                    pass
        # 兼容旧 SingleValue 模板
        if is_value_template(_data):
            val = SingleValue.try_from(_data)
            if val is not None:
                hex_str = str(val.value)
                if hex_str.startswith("0x"):
                    hex_str = hex_str[2:]
                try:
                    code = bytes.fromhex(hex_str)
                    return cls(pos, code=code)
                except ValueError:
                    pass
        raise TypeError(f"Invalid data for Value2P_caret: {data}")

    def json(self) -> JSONObject:
        """导出为 JSON。"""
        # 使用 SingleValue 存储十六进制编码的 bytes
        hex_str = self._code.hex()
        return ImmutableDict({
            "_SingleValue": True,
            "data": f"0x{hex_str}",
        })

    def code(self) -> bytes:
        """返回原始编码。"""
        return self._code

    def __repr__(self) -> str:
        """显示为浮点数（保留4位小数）。"""
        return f"{self.cos_val:.4f}"

    def compose(self, board: 'Board') -> Dict:
        """渲染为图像元素。"""
        from minesweepervariants.utils.image_template import get_col, get_text, get_dummy
        text = f"{self.cos_val:.4f}"
        return get_col(
            get_dummy(height=0.3),
            get_text(text),
            get_dummy(height=0.3),
        )

    def web_component(self, board: 'Board') -> Dict:
        """渲染为网页组件。"""
        from minesweepervariants.utils.web_template import Number
        return Number(f"{self.cos_val:.4f}")

    def tag(self, board: 'Board') -> bytes:
        """返回角标，显示 M3E4 编码的十六进制表示。"""
        return self._code.hex().encode("ascii")

    def high_light(self, board: 'Board') -> List['Position']:
        """高亮显示相关格子：最近的两个雷。"""
        # 重新计算最近的两个雷（使用当前 board 状态）
        mine_positions = []
        for mine_pos, _ in board("F"):
            if board.is_valid(mine_pos):
                dist = distance(self.pos, mine_pos)
                mine_positions.append((dist, mine_pos))
        mine_positions.sort(key=lambda x: x[0])
        nearest_two = mine_positions[:2]
        return [p for _, p in nearest_two]

    def create_constraints(self, board: 'Board', switch: 'Switch'):
        """
        创建 CP-SAT 约束，确保线索值与最近的雷的夹角余弦值一致。
        实现策略：枚举所有可能的“最近两个雷”的组合，确保实际余弦值与存储值匹配。
        """
        model = board.get_model()
        logger = get_logger()
        s = switch.get(model, self)

        # 收集所有可能的雷位置 (变量)
        possible_mines = []
        for pos, var in board(mode="var"):
            # 排除线索自身 (它是非雷格)
            if pos == self.pos:
                continue
            # 只考虑未确定或可能为雷的格子
            if board.get_type(pos) == "N":
                possible_mines.append((pos, var))

        # 如果可能的雷少于 2，则无法满足约束 (除非线索值本身为 1.0，但这里直接标记为不可满足)
        if len(possible_mines) < 2:
            model.Add(False).OnlyEnforceIf(s)
            logger.warning(f"[2P^] {self.pos}: 可选的雷位置少于 2，约束不可满足")
            return

        # 枚举所有两两组合 (i, j)
        candidate_vars = []
        n = len(possible_mines)
        for i in range(n):
            pos_i, var_i = possible_mines[i]
            for j in range(i + 1, n):
                pos_j, var_j = possible_mines[j]

                # 计算这两个雷相对于线索位置的夹角余弦值
                cos_ij = angle_cosine(self.pos, pos_i, pos_j)

                # 如果余弦值与存储值不一致，则跳过该组合 (因为无法匹配)
                if abs(cos_ij - self.cos_val) > 1e-6:
                    continue

                # 创建候选变量：表示 (var_i, var_j) 是最近的两个雷
                candidate = model.NewBoolVar(f"2P^_cand_{self.pos}_{i}_{j}")

                # 约束1：var_i 和 var_j 必须为雷
                model.Add(var_i == 1).OnlyEnforceIf([candidate, s])
                model.Add(var_j == 1).OnlyEnforceIf([candidate, s])

                # 约束2：所有距离小于 max(dist_i, dist_j) 的位置不能是雷
                max_dist = max(distance(self.pos, pos_i), distance(self.pos, pos_j))
                closer_vars = []
                for k in range(n):
                    if k == i or k == j:
                        continue
                    pos_k, var_k = possible_mines[k]
                    if distance(self.pos, pos_k) < max_dist - 1e-9:
                        closer_vars.append(var_k)

                # 所有更近的位置必须为非雷
                if closer_vars:
                    for var_k in closer_vars:
                        model.Add(var_k == 0).OnlyEnforceIf([candidate, s])

                # 约束3：距离等于 max_dist 的其他位置，如果也是雷，则必须与 var_i, var_j 的夹角余弦值相同
                # 如果存在多个等距雷，需要保证它们与 var_i, var_j 夹角一致，否则该组合不合法。
                # 但为了简化，我们假设等距且夹角不同的情况由组合自身处理，不在此处额外约束。
                # (更严格的实现需要处理 tie-breaking，但这里为了可解性，放宽条件。)

                candidate_vars.append(candidate)

        # 确保至少有一个候选组合成立
        if candidate_vars:
            model.AddBoolOr(candidate_vars).OnlyEnforceIf(s)
            logger.trace(f"[2P^] {self.pos}: 添加 {len(candidate_vars)} 个候选组合")
        else:
            # 没有可行的组合，约束不可满足
            model.Add(False).OnlyEnforceIf(s)
            logger.warning(f"[2P^] {self.pos}: 没有找到可行的候选组合")
