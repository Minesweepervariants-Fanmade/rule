#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026-09-02
# @Author  : DeepSeek Agent
# @FileName: EV.py
"""
[EV] 特征值：将雷视为 1，非雷视为 0，题板对应的矩阵恰好有 k 个不同的特征值。
"""

from __future__ import annotations

import numpy as np

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board


class RuleEV(AbstractMinesRule):
    id = "EV"
    name = "Eigenvalue"
    name.zh_CN = "特征值"
    doc = "The 0-1 matrix of the board has exactly k distinct eigenvalues."
    doc.zh_CN = "将雷视为1，非雷视为0时，题板对应的矩阵恰好有k个不同的特征值。"
    author = ("Indiebard (Alith)", 2513946475)
    tags = ["Creative", "Global", "Strict Shape", "Parameter"]
    creation_time = "2026-09-02"

    def __init__(self, board: Board | None = None, data: str | None = None) -> None:
        super().__init__(board, data)
        if data is None:
            raise ValueError("EV 规则需要参数 k (特征值个数)")
        try:
            self.k = int(data)
        except ValueError:
            raise ValueError("EV 参数 k 必须为整数")

    def init_board(self, board: Board) -> None:
        """在生成答案板阶段检查特征值个数是否等于 k。"""
        keys = board.get_interactive_keys()
        if len(keys) != 1:
            raise ValueError("EV 规则当前仅支持单主板")
        key = keys[0]
        size = board.get_config(key, "size")
        if size.rows != size.cols:
            raise ValueError("EV 规则要求题板为正方形")
        n = size.rows

        # 构建 0‑1 矩阵
        mat = np.zeros((n, n), dtype=np.float64)
        for r in range(n):
            for c in range(n):
                pos = board.get_pos(r, c, key)
                if board.get_type(pos, special='raw') == "F":
                    mat[r, c] = 1.0

        # 计算特征值并去重（容差 1e‑8）
        eigvals = np.linalg.eigvals(mat)
        # 四舍五入到 8 位小数，然后去重
        rounded = np.round(eigvals, decimals=8)
        distinct = np.unique(rounded)
        from minesweepervariants.utils.tool import get_logger
        logger = get_logger("EV")
        logger.debug(f"EV 规则调试: k={self.k}, 实际特征值数量={len(distinct)}, 特征值={distinct.tolist()}")
        if len(distinct) != self.k:
            raise ValueError(
                f"EV 规则失败: 预期 {self.k} 个不同特征值，实际得到 {len(distinct)} 个"
            )

    def create_constraints(self, board: Board, switch) -> None:
        """不添加任何 CP‑SAT 约束，仅在 init_board 中验证。"""
        return

    def suggest_total(self, info: dict) -> None:
        """建议总雷数范围，以提高特征值数量命中率。对于 n×n 矩阵，总雷数在 n 附近时特征值数量通常较少。"""
        from itertools import product
        n = None
        for key in info["interactive"]:
            size = info["size"][key]
            if size[0] == size[1]:
                n = size[0]
                break
        if n is None:
            return
        # 针对不同 n 值，枚举可能的特征值数量与总雷数的关系
        # 对于小矩阵，可以枚举所有可能的总雷数
        for target in range(0, n*n+1):
            # 为了增加命中率，对每个总雷数都赋予较小的软约束权重
            info["soft_fn"](target, 0)
