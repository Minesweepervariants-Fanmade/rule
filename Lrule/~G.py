#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/08/04 08:37
# @Author  : 世界第二睦推 (992600401)
# @FileName: ~G.py
"""
[~G]重心非雷: 题板任意三个雷的重心不能是雷。仅限该重心是整点的情况。
"""

from typing import Optional
from itertools import combinations

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.position import Position


class TildeG(AbstractMinesRule):
    """
    重心非雷规则：题板上任意三个雷的重心不能是雷。仅限该重心是整点的情况。
    """
    id = "~G"
    aliases = ()
    name = "Center of Gravity"
    name.zh_CN = "重心非雷"
    doc = "The center of gravity of any three mines cannot be a mine. Only valid when the center is an integer point."
    doc.zh_CN = "题板任意三个雷的重心不能是雷。仅限该重心是整点的情况。"
    author = ("世界第二睦推 (992600401)", 992600401)
    tags = ["Anti-Construction", "Local", "Global"]
    creation_time = "2026-08-04"

    def create_constraints(self, board: Board, switch):
        """
        添加约束：对于任意三个不同的位置，如果它们都是雷，且重心是整点且在板内，则重心位置不能是雷。
        """
        model = board.get_model()
        if model is None:
            return

        # 获取当前规则的开关变量
        rule_switch = switch.get(model, self)

        # 收集所有有效位置的 raw 变量（直接通过 board_data 访问，确保获取到所有变量）
        positions = []
        variables = {}
        
        from minesweepervariants.board import MASTER_BOARD_KEY
        if MASTER_BOARD_KEY not in board.board_data:
            return
        
        data = board.board_data[MASTER_BOARD_KEY]
        if "variable" not in data:
            return
        
        var_matrix = data["variable"]
        config = data["config"]
        size = config["size"]
        
        # 遍历所有位置，直接从 var_matrix 获取变量
        for row in range(size.rows):
            for col in range(size.cols):
                pos = Position(col, row, MASTER_BOARD_KEY)
                if board.is_valid(pos):
                    var = var_matrix.get(pos)  # 直接获取，不使用 board.get_variable
                    if var is not None:
                        positions.append(pos)
                        variables[pos] = var

        n = len(positions)
        if n < 3:
            # 如果变量不足3个，无法形成三元组，直接返回
            return

        # 遍历所有三元组
        for p1, p2, p3 in combinations(positions, 3):
            # 计算重心坐标（列和行分别求和）
            sum_col = p1.col + p2.col + p3.col
            sum_row = p1.row + p2.row + p3.row

            # 检查重心是否为整点
            if sum_col % 3 != 0 or sum_row % 3 != 0:
                continue

            # 重心坐标
            gx = sum_col // 3
            gy = sum_row // 3

            # 创建重心位置（使用与p1相同的键）
            gravity_pos = Position(gx, gy, p1.board_key)

            # 检查重心是否在板内且有效
            if not board.is_valid(gravity_pos):
                continue

            # 获取重心位置的变量（直接从矩阵获取）
            var_g = var_matrix.get(gravity_pos)
            if var_g is None:
                continue

            # 获取三个位置的变量
            var1 = variables.get(p1)
            var2 = variables.get(p2)
            var3 = variables.get(p3)
            
            if var1 is None or var2 is None or var3 is None:
                continue

            # 添加约束：如果p1,p2,p3都是雷，则重心不能是雷
            # 即：var1 AND var2 AND var3 => var_g == 0
            # 等价于：NOT var1 OR NOT var2 OR NOT var3 OR NOT var_g
            # 直接添加约束，不依赖rule_switch，确保约束始终生效
            model.AddBoolOr([
                var1.Not(),
                var2.Not(),
                var3.Not(),
                var_g.Not()
            ])

    def suggest_total(self, info: dict):
        """
        建议雷总数。此规则本身不强制特定总数。
        """
        pass

    def init_board(self, board: Board) -> bool:
        """
        初始化题板时无需特殊操作。
        """
        return True

    def init_clear(self, board: Board) -> None:
        """
        清除阶段无需特殊操作。
        """
        pass

    def combine(self, other) -> Optional['TildeG']:
        """
        规则合并优化：不支持合并。
        """
        return None

    def get_deps(self) -> list[str]:
        """
        返回依赖的其他规则名称列表。此规则无依赖。
        """
        return []
