#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/15
# @Author  : NT (2201963934)
# @FileName: 7SD.py
"""
[7SD] 七段数码管：左线规则

定义：
盘面上每个3x5区域的15格中：
- 四个角以及左右两边中点的格子称为顶点格（共6个）
- 中心格上下两格称为内面格（共2个）
- 其余7格称为段格（共7个）
- 其外部相邻的16格称为外面格（上下各3格，左右各5格）

一个3x5区域是数码管，当且仅当：
1. 段格和顶点格组成的图案是一个合法的0-F数码管标准图案
2. 该数码管的内面格与外面格的雷数之和等于该数码管表示的数位数值

约束：盘面上至少有一个数码管。
"""

from typing import List, Tuple

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board, Position
from minesweepervariants.utils.tool import get_logger


# 七段数码管段映射（段格索引 -> 标准段名 a-g）
# 段格在3x5区域中的偏移量 (dr, dc)
SEGMENT_OFFSETS: List[Tuple[int, int]] = [
    (0, 1),  # a
    (0, 2),  # b
    (0, 3),  # c
    (1, 2),  # d
    (2, 1),  # e
    (2, 2),  # f
    (2, 3),  # g
]

# 顶点格偏移量 (dr, dc) —— 四个角 + 左右两边中点
VERTEX_OFFSETS: List[Tuple[int, int]] = [
    (0, 0), (0, 4),  # 上角
    (2, 0), (2, 4),  # 下角
    (1, 0), (1, 4),  # 左右中点
]

# 内面格偏移量 (dr, dc) —— 中心格上下两格
INNER_OFFSETS: List[Tuple[int, int]] = [
    (1, 1), (1, 3),
]

# 外面格偏移量 (dr, dc) —— 上下各3格，左右各5格
OUTER_OFFSETS: List[Tuple[int, int]] = [
    # 上方3格 (行-1, 列 c+1 ~ c+3)
    (-1, 1), (-1, 2), (-1, 3),
    # 下方3格 (行+3, 列 c+1 ~ c+3)
    (3, 1), (3, 2), (3, 3),
    # 左方5格 (列-1, 行 r-1 ~ r+3)
    (-1, -1), (0, -1), (1, -1), (2, -1), (3, -1),
    # 右方5格 (列+5, 行 r-1 ~ r+3)
    (-1, 5), (0, 5), (1, 5), (2, 5), (3, 5),
]

# 数字0-F的七段编码（a-g依次为1表示该段点亮/有雷）
# 索引0-9对应数字0-9, 10-15对应A-F
SEGMENT_PATTERNS: List[List[int]] = [
    [1, 1, 1, 1, 1, 1, 0],  # 0: a,b,c,d,e,f on, g off
    [0, 1, 1, 0, 0, 0, 0],  # 1: b,c on
    [1, 1, 0, 1, 1, 0, 1],  # 2: a,b,d,e,g on
    [1, 1, 1, 1, 0, 0, 1],  # 3: a,b,c,d,g on
    [0, 1, 1, 0, 0, 1, 1],  # 4: b,c,f,g on
    [1, 0, 1, 1, 0, 1, 1],  # 5: a,c,d,f,g on
    [1, 0, 1, 1, 1, 1, 1],  # 6: a,c,d,e,f,g on
    [1, 1, 1, 0, 0, 0, 0],  # 7: a,b,c on
    [1, 1, 1, 1, 1, 1, 1],  # 8: all on
    [1, 1, 1, 1, 0, 1, 1],  # 9: a,b,c,d,f,g on
    [1, 1, 1, 0, 1, 1, 1],  # A: a,b,c,e,f,g on
    [0, 0, 1, 1, 1, 1, 1],  # b: c,d,e,f,g on (小写b)
    [1, 0, 0, 1, 1, 1, 0],  # C: a,d,e,f on
    [0, 1, 1, 1, 1, 0, 1],  # d: b,c,d,e,g on (小写d)
    [1, 0, 0, 1, 1, 1, 1],  # E: a,d,e,f,g on
    [1, 0, 0, 0, 1, 1, 1],  # F: a,e,f,g on
]


class Rule7SD(AbstractMinesRule):
    """七段数码管左线规则"""

    id = "7SD"
    name = "Seven-Segment Display"
    name.zh_CN = "七段数码管"
    doc = (
        "A 3x5 region is a digit display if its segment and vertex cells form "
        "a valid 0-F seven-segment pattern, and the sum of mines in its inner "
        "and outer cells equals the displayed digit. At least one such region "
        "must exist on the board."
    )
    doc.zh_CN = (
        "盘面上存在至少一个3x5区域，其段格与顶点格构成的图案为合法的0-F数码管标准图案，"
        "且该数码管的内面格与外面格雷数之和等于其表示的数位数值。"
    )
    author = ("NT", 2201963934)
    tags = ["Creative", "Local", "Strong"]
    creation_time = "2026-07-15"

    def create_constraints(self, board: 'Board', switch):
        """
        为七段数码管规则添加约束。
        """
        model = board.get_model()
        s = switch.get(model, self)
        # 强制规则启用
        model.Add(s == 1)
        logger = get_logger()

        main_key = board.get_board_keys()[0]
        bound = board.boundary(main_key)
        rows = bound.row + 1
        cols = bound.col + 1
        main_key = board.get_board_keys()[0]
        region_switches = []

        # 遍历所有可能的3x5区域左上角
        for r in range(rows - 2):      # 区域高度为3
            for c in range(cols - 4):  # 区域宽度为5
                # 检查区域内所有涉及的格子是否都在题板内
                all_positions = []
                valid = True

                # 只检查段格和顶点格必须存在（内面格和外面格允许在边界外，视为非雷）
                core_offsets = SEGMENT_OFFSETS + VERTEX_OFFSETS
                for dr, dc in core_offsets:
                    pos = Position(r + dr, c + dc, main_key)
                    if not board.in_bounds(pos):
                        valid = False
                        break
                if not valid:
                    continue

                # 创建该区域的开关变量
                region_switch = model.NewBoolVar(f"7sd_region_{r}_{c}")
                region_switches.append(region_switch)

                # 为该区域创建16个数字开关（0-F）
                digit_switches = []
                for d in range(16):
                    digit_switch = model.NewBoolVar(f"7sd_region_{r}_{c}_digit_{d}")
                    digit_switches.append(digit_switch)

                    # 段格约束：根据数字d的段模式强制段格变量为0或1
                    for seg_idx, (dr, dc) in enumerate(SEGMENT_OFFSETS):
                        pos = Position(r + dr, c + dc, main_key)
                        var = board.get_variable(pos)
                        if SEGMENT_PATTERNS[d][seg_idx] == 1:
                            model.Add(var == 1).OnlyEnforceIf([digit_switch])
                        else:
                            model.Add(var == 0).OnlyEnforceIf([digit_switch])

                    # 顶点格约束：全部为非雷（0）
                    for dr, dc in VERTEX_OFFSETS:
                        pos = Position(r + dr, c + dc, main_key)
                        var = board.get_variable(pos)
                        model.Add(var == 0).OnlyEnforceIf([digit_switch])

                    # 内面格 + 外面格雷数之和等于数字d（边界外视为非雷）
                    inner_outer_vars = []
                    for dr, dc in INNER_OFFSETS + OUTER_OFFSETS:
                        pos = Position(r + dr, c + dc, main_key)
                        if board.in_bounds(pos):
                            var = board.get_variable(pos)
                            inner_outer_vars.append(var)
                        else:
                            # 边界外视为非雷（值为0）
                            inner_outer_vars.append(0)
                    model.Add(sum(inner_outer_vars) == d).OnlyEnforceIf([digit_switch])

                # 区域开关为真时，恰好一个数字开关为真
                model.Add(sum(digit_switches) == 1).OnlyEnforceIf([region_switch])
                # 区域开关为假时，所有数字开关为假（即 digit_switches 之和为0）
                model.Add(sum(digit_switches) == 0).OnlyEnforceIf([region_switch.Not()])

                logger.trace(f"[7SD] 添加区域约束: ({r},{c})")

        # 至少存在一个数码管
        if region_switches:
            model.Add(sum(region_switches) >= 1)
            logger.trace(f"[7SD] 至少需要一个数码管，共 {len(region_switches)} 个候选区域")
        else:
            # 如果没有任何有效区域，则规则无法满足
            logger.warning("[7SD] 没有找到任何有效的3x5区域，规则无法满足")
            # 使用一个简单的线性表达式来强制无解
            # 创建一个永远为0的变量，然后要求它等于1
            dummy_var = model.NewIntVar(0, 0, f"7sd_dummy_no_region")
            model.Add(dummy_var == 1)

    def suggest_total(self, info: dict):
        """
        建议雷总数（可选）。
        此规则不强制总雷数，因此不添加任何建议。
        """
        pass
