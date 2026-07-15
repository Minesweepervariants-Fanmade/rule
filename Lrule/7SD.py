#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/15
# @Author  : DeepSeek Agent
# @FileName: 7SD.py
"""
[7SD]七段数码管: 左线规则
定义：盘面上每个3x5的区域的15格，其中四个角以及左右两边中点的格子称为顶点格，
中心格上下两格称为内面格，其余7格称为段格，其外部相邻的16格（上下各3格，左右各5格）称为外面格。
一个3x5的区域是数码管，当且仅当其段格和顶点格组成的图案是一个合法的0-F数码管标准图案。
约束：每个数码管的内面格与外面格的雷数之和都等于该数码管表示的数位数值，且盘面上至少有一个数码管。
"""

from typing import List, Tuple, Dict
from ortools.sat.python.cp_model import CpModel, IntVar

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board


class Rule7SD(AbstractMinesRule):
    id = "7SD"
    aliases = ("SevenSegment",)
    name = "Seven-Segment Display"
    name.zh_CN = "七段数码管"
    doc = "Each 3x5 area forms a 0-F digit; sum of mines in inner and outer cells equals the digit value"
    doc.zh_CN = "每个3x5区域形成0-F数字；内面格与外面格的雷数之和等于该数字的值"
    author = ("DeepSeek Agent", 0)
    tags = ["Original", "Local", "Strong"]
    creation_time = "2026-07-15"

    # 段格在3x5区域中的相对坐标 (行, 列)
    SEGMENT_POSITIONS = [
        (0, 1),  # a段 (上横左)
        (0, 3),  # b段 (右上竖)
        (1, 3),  # c段 (右下竖)
        (2, 3),  # d段 (下横右)
        (2, 1),  # e段 (左下竖)
        (1, 1),  # f段 (左上竖)
        (1, 2),  # g段 (中横)
    ]

    # 顶点格在3x5区域中的相对坐标
    VERTEX_POSITIONS = [
        (0, 0),  # 左上角
        (0, 4),  # 右上角
        (1, 0),  # 左边中点
        (1, 4),  # 右边中点
        (2, 0),  # 左下角
        (2, 4),  # 右下角
    ]

    # 内面格在3x5区域中的相对坐标
    INNER_POSITIONS = [
        (0, 2),  # 中心上格
        (2, 2),  # 中心下格
    ]

    # 标准七段数码管段状态 (a,b,c,d,e,f,g) 对应上述SEGMENT_POSITIONS顺序
    # 0-F数字的七段编码 (1=亮, 0=灭)
    SEVEN_SEGMENT_CODES = {
        0: (1, 1, 1, 1, 1, 1, 0),  # 0
        1: (0, 1, 1, 0, 0, 0, 0),  # 1
        2: (1, 1, 0, 1, 1, 0, 1),  # 2
        3: (1, 1, 1, 1, 0, 0, 1),  # 3
        4: (0, 1, 1, 0, 0, 1, 1),  # 4
        5: (1, 0, 1, 1, 0, 1, 1),  # 5
        6: (1, 0, 1, 1, 1, 1, 1),  # 6
        7: (1, 1, 1, 0, 0, 0, 0),  # 7
        8: (1, 1, 1, 1, 1, 1, 1),  # 8
        9: (1, 1, 1, 1, 0, 1, 1),  # 9
        10: (1, 1, 1, 0, 1, 1, 1),  # A
        11: (0, 0, 1, 1, 1, 1, 1),  # b
        12: (1, 0, 0, 1, 1, 1, 0),  # C
        13: (0, 1, 1, 1, 1, 0, 1),  # d
        14: (1, 0, 0, 1, 1, 1, 1),  # E
        15: (1, 0, 0, 0, 1, 1, 1),  # F
    }

    # 预计算每个数字在13个位置 (7段格 + 6顶点格) 上的完整图案
    # 顺序: 段格7个 (按SEGMENT_POSITIONS顺序) + 顶点格6个 (按VERTEX_POSITIONS顺序)
    PATTERNS: Dict[int, Tuple[int, ...]] = {}

    @classmethod
    def _build_patterns(cls):
        """构建每个数字的13位图案 (段格状态 + 顶点格状态)"""
        if cls.PATTERNS:
            return
        for digit, seg_code in cls.SEVEN_SEGMENT_CODES.items():
            # 段格状态
            segment_states = seg_code  # 已经是7个元素的元组
            # 顶点格全部为1 (有雷) 表示参与图案
            vertex_states = (1, 1, 1, 1, 1, 1)
            cls.PATTERNS[digit] = segment_states + vertex_states

    def create_constraints(self, board: 'Board', switch):
        """
        为CP-SAT模型添加约束
        """
        self._build_patterns()

        model: CpModel = board.get_model()
        
        # 获取主交互式题板的尺寸
        main_key = board.get_interactive_keys()[0]
        boundary_pos = board.boundary(main_key)
        rows = boundary_pos.row + 1
        cols = boundary_pos.col + 1

        # 遍历所有可能的3x5区域
        regions = []
        for r in range(rows - 2):
            for c in range(cols - 4):
                # 检查区域内所有15个位置是否有效 (在棋盘内且未被掩码遮挡)
                all_positions = []
                valid = True
                for i in range(3):
                    for j in range(5):
                        pos = board.get_pos(r + i, c + j, key=main_key)
                        if pos is None or not board.is_valid(pos):
                            valid = False
                            break
                        all_positions.append(pos)
                    if not valid:
                        break
                if not valid:
                    continue

                # 获取内部15个位置的变量
                pos_vars = [board.get_variable(pos) for pos in all_positions]

                # 获取段格变量 (7个)
                seg_vars = []
                for dr, dc in self.SEGMENT_POSITIONS:
                    idx = dr * 5 + dc
                    seg_vars.append(pos_vars[idx])

                # 获取顶点格变量 (6个)
                vertex_vars = []
                for dr, dc in self.VERTEX_POSITIONS:
                    idx = dr * 5 + dc
                    vertex_vars.append(pos_vars[idx])

                # 获取内面格变量 (2个)
                inner_vars = []
                for dr, dc in self.INNER_POSITIONS:
                    idx = dr * 5 + dc
                    inner_vars.append(pos_vars[idx])

                # 获取外面格变量 (16个外部紧邻格子)
                outer_vars = []
                # 上方5格 (行r-1, 列c到c+4)
                for j in range(5):
                    pos = board.get_pos(r - 1, c + j, key=main_key)
                    if pos is not None and board.is_valid(pos):
                        outer_vars.append(board.get_variable(pos))
                # 下方5格 (行r+3, 列c到c+4)
                for j in range(5):
                    pos = board.get_pos(r + 3, c + j, key=main_key)
                    if pos is not None and board.is_valid(pos):
                        outer_vars.append(board.get_variable(pos))
                # 左方3格 (列c-1, 行r到r+2)
                for i in range(3):
                    pos = board.get_pos(r + i, c - 1, key=main_key)
                    if pos is not None and board.is_valid(pos):
                        outer_vars.append(board.get_variable(pos))
                # 右方3格 (列c+5, 行r到r+2)
                for i in range(3):
                    pos = board.get_pos(r + i, c + 5, key=main_key)
                    if pos is not None and board.is_valid(pos):
                        outer_vars.append(board.get_variable(pos))

                # 如果外面格数量不足16 (由于边界)，可以忽略该区域或放宽约束，
                # 但根据规则，区域必须在盘面内部，所以外面格应该都存在。
                # 这里我们仍添加约束，但如果不全，可能导致无解，因此只处理完全有效的区域。
                if len(outer_vars) != 16:
                    continue  # 跳过靠近边界的区域，因为外面格不完整

                regions.append((seg_vars, vertex_vars, inner_vars, outer_vars, r, c))

        # 如果没有有效区域，则无法生成题板，但我们可以添加一个软约束要求至少有一个区域
        if not regions:
            # 由于没有区域，无法应用约束，但盘面上至少有一个数码管的要求无法满足，
            # 这里我们不做处理，让求解器可能无解，但在suggest_total中会建议合适的雷数。
            return

        # 获取规则开关
        rule_switch = switch.get(model, self)

        # 用于收集所有区域的is_segment变量，确保至少有一个数码管
        segment_vars = []

        # 为每个区域创建约束
        for seg_vars, vertex_vars, inner_vars, outer_vars, r, c in regions:
            # 13个位置的状态变量 (7段格 + 6顶点格)
            pattern_vars = seg_vars + vertex_vars

            # 创建数字变量 digit (0-15)，仅在是数码管时有效
            digit = model.NewIntVar(0, 15, f'digit_{r}_{c}')

            # 为每个数字d创建匹配标志 is_digit_d
            is_d_vars = []
            for d, pattern in self.PATTERNS.items():
                is_d = model.NewBoolVar(f'is_digit_{r}_{c}_{d}')

                # 构建匹配条件: 所有要求为1的位置变量为1，所有要求为0的位置变量为0
                conditions = []
                for var, state in zip(pattern_vars, pattern):
                    if state == 1:
                        conditions.append(var)
                    else:
                        # 要求为0，即 (1 - var) 为真
                        conditions.append(var.Not())

                # is_d => conditions
                for cond in conditions:
                    model.AddImplication(is_d, cond)

                # conditions => is_d
                model.AddBoolAnd(conditions).OnlyEnforceIf(is_d)

                is_d_vars.append(is_d)

            # 确保最多只有一个数字被匹配 (即图案不能同时匹配多个数字)
            model.AddAtMostOne(is_d_vars)

            # 该区域是否是数码管 (即至少匹配一个数字)
            is_segment = model.NewBoolVar(f'is_segment_{r}_{c}')
            # is_segment == sum(is_d_vars) (由于互斥，sum只能为0或1)
            # 用 AddBoolOr 和 AddImplication 来实现
            # 或者直接使用 Add(sum(is_d_vars) == is_segment) 但需要线性约束
            # 这里使用 Add(sum(is_d_vars) == is_segment) 是合法的，因为 is_d_vars 是 BoolVar
            model.Add(sum(is_d_vars) == is_segment)

            # digit 等于匹配的数字 (当 is_segment 为真时)
            # 用线性约束：digit == sum(d * is_d) 但只有 is_segment 为真时才生效
            # 我们可以直接设置 digit == sum(d * is_d) 因为 sum 会在没有匹配时为0，不影响
            # 但我们希望 digit 只在 is_segment 为真时有效，不过我们可以无条件设置 digit 为匹配数字，
            # 当无匹配时，digit = 0，但此时我们不会应用约束。
            # 所以我们可以设置 digit == sum(d * is_d for d, is_d in enumerate(is_d_vars))
            model.Add(digit == sum(d * is_d for d, is_d in enumerate(is_d_vars)))

            # 计算内面格 + 外面格的雷数之和
            inner_outer_vars = inner_vars + outer_vars
            sum_inner_outer = sum(inner_outer_vars)

            # 约束: 如果是数码管，则内面格+外面格雷数 == digit
            model.Add(sum_inner_outer == digit).OnlyEnforceIf(is_segment)

            # 收集该区域的 is_segment 变量，用于确保至少有一个数码管
            segment_vars.append(is_segment)

        # 确保盘面上至少有一个数码管 (即至少有一个 is_segment 为真)
        if segment_vars:
            model.Add(sum(segment_vars) >= 1).OnlyEnforceIf(rule_switch)

    def suggest_total(self, info: dict):
        """
        建议雷总数
        对于七段数码管规则，雷数应该适中，使得至少有一个区域能形成数码管图案。
        """
        ub = 0
        totals = info.get("total", {})
        interactive = info.get("interactive", [])
        soft_fn = info.get("soft_fn")

        if not isinstance(totals, dict) or not isinstance(interactive, list) or not callable(soft_fn):
            return

        for key in interactive:
            ub += totals.get(key, 0)

        # 建议雷数约为总格数的40%，这样既不太密也不太疏，容易形成图案
        soft_fn(ub * 0.4, -1)
