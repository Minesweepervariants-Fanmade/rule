#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/03/01 13:28:35
# @Author  : 咸鱼 (3898637422)
# @FileName: NM.py
"""
[NM] 标记格数值等于周围8格中染色格雷数乘以非染色格中非雷格数

规则语义：
- 右线规则(Rrule), 每个线索格（非雷格）显示一个数值。
- 线索值 = (周围8格中染色格且为雷的数量) * (周围8格中非染色格且为非雷的数量)。
- 染色状态通过 board.get_dyed(pos) 获取。
- 边界外格子不参与统计。
"""
from typing import List
from ortools.sat.python.cp_model import IntVar
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import JSONObject, deep_unwrap
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position
from ....utils.tool import get_logger


class RuleNM(AbstractClueRule):
    id = "NM"
    name = "NM"
    name.zh_CN = "NM"
    doc = "Clue value equals the product of the number of dyed mines and the number of undyed non-mines among the 8 surrounding cells."
    doc.zh_CN = "标记格数值等于周围8格中染色格雷数乘以非染色格中非雷格数。"
    tags = ["Variant", "Local", "Number Clue", "Dyed"]
    creation_time = "2026-03-01 13:28:35"
    author = ("咸鱼", 3898637422)

    def fill(self, board: 'Board') -> 'Board':
        """
        根据答案题板填充所有非雷格（N 类型）为 NM 线索。
        """
        logger = get_logger()
        for pos, _ in board("N", special='raw'):
            # 获取周围8格（包括边界内有效格子）
            neighbors = [p for p in pos.neighbors(2) if board.in_bounds(p)]

            # 计算染色雷数和非染色非雷数
            dyed_mine_count = 0
            undyed_non_mine_count = 0
            for p in neighbors:
                is_mine = (board.get_type(p, special='raw') == 'F')
                is_dyed = board.get_dyed(p)
                if is_mine and is_dyed:
                    dyed_mine_count += 1
                elif (not is_mine) and (not is_dyed):
                    undyed_non_mine_count += 1

            # 线索值 = 乘积
            clue_value = dyed_mine_count * undyed_non_mine_count
            board.set_value(pos, ValueNM(pos, count=clue_value))
            logger.trace(f"[NM] {pos}: dyed_mine={dyed_mine_count}, undyed_non_mine={undyed_non_mine_count} -> {clue_value}")

        return board

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        """
        为 NM 规则添加约束：
        对每个 NM 线索格，创建变量表示周围染色格雷数和非染色非雷数，
        并约束其乘积等于线索值。
        """
        model = board.get_model()
        # 规则开关（NM 规则作为整体启用）
        rule_switch = switch.get(model, self)

        # 收集所有 ValueNM 线索格的开关
        clue_switches = []
        for pos, obj in board(mode="obj"):
            if not isinstance(obj, ValueNM):
                continue
            # 获取该线索格的独立开关
            s = switch.get(model, pos)
            clue_switches.append(s)

        # 强制所有线索格的开关必须为真（即所有线索必须激活）
        # 这样线索格的约束就必须被满足，从而正确检测违反规则的情况
        if clue_switches:
            model.Add(sum(clue_switches) == len(clue_switches)).OnlyEnforceIf(rule_switch)
        return


class ValueNM(AbstractClueValue):
    id = RuleNM.id

    def __init__(self, pos: Position, count: int = 0):
        super().__init__(pos, b'')
        self.count = count
        # 存储周围格子位置（用于高亮和约束）
        self.neighbor = [p for p in pos.neighbors(2) if pos.in_bounds(p)]  # 注意：这里需要用到 board，但构造时尚未传入，此处不能直接过滤
        # 改为在需要时通过 board 计算
        self._neighbor_cache = None
        self.value = SingleIntValue(self.count)

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)
        if not is_value_template(_data):
            raise TypeError("Invalid value template for NM clue")
        value = SingleIntValue.try_from(_data)
        if value is None:
            raise ValueError("Failed to parse NM clue value from JSON")
        return cls(pos, count=value.value)

    def high_light(self, board: 'Board') -> List['Position']:
        """高亮显示周围8格（用于前端提示）"""
        if self._neighbor_cache is None:
            self._neighbor_cache = [p for p in self.pos.neighbors(2) if board.in_bounds(p)]
        return self._neighbor_cache

    def invalid(self, board: 'Board') -> bool:
        """如果周围8格全部翻开（无 N 类型），则线索可验证，视为无效（可删除）"""
        neighbors = self.high_light(board)
        return board.batch(neighbors, mode="type", special='raw').count("N") == 0

    def create_constraints(self, board: 'Board', switch: Switch):
        """
        创建 CP-SAT 约束：
        - 线索值 = (周围染色格雷数) * (周围非染色非雷格数)
        """
        model = board.get_model()
        logger = get_logger()

        # 获取该线索的开关
        s = switch.get(model, self.pos)

        # 强制该线索格自身为非雷（这是右线规则的基础要求）
        mine_self = board.get_variable(self.pos, special='raw')
        if mine_self is not None:
            model.Add(mine_self == 0).OnlyEnforceIf(s)

        # 获取周围8格有效位置
        neighbors = [p for p in self.pos.neighbors(2) if board.in_bounds(p)]
        if not neighbors:
            # 如果没有邻居（1x1 棋盘），则线索值只能为0
            model.Add(self.count == 0).OnlyEnforceIf(s)
            logger.trace(f"[NM] {self.pos}: no neighbors, count must be 0")
            return

        # 创建两个整数变量表示染色雷数和非染色非雷数
        dyed_mine_sum = model.NewIntVar(0, 8, f"nm_dyed_mine_sum_{self.pos.row}_{self.pos.col}")
        undyed_non_mine_sum = model.NewIntVar(0, 8, f"nm_undyed_non_mine_sum_{self.pos.row}_{self.pos.col}")

        # 分别统计染色雷和非染色非雷
        dyed_mine_vars = []
        undyed_non_mine_vars = []
        for p in neighbors:
            mine_var = board.get_variable(p, special='raw')
            if mine_var is None:
                continue
            is_dyed = board.get_dyed(p)
            if is_dyed:
                dyed_mine_vars.append(mine_var)
            else:
                # 非染色非雷：1 - mine_var
                non_mine_var = model.NewBoolVar(f"nm_non_mine_{p.row}_{p.col}")
                model.Add(non_mine_var == 1 - mine_var)
                undyed_non_mine_vars.append(non_mine_var)

        # 约束 sum 等于实际数量（不依赖 s，因为统计是客观事实）
        if dyed_mine_vars:
            model.Add(dyed_mine_sum == sum(dyed_mine_vars))
        else:
            model.Add(dyed_mine_sum == 0)

        if undyed_non_mine_vars:
            model.Add(undyed_non_mine_sum == sum(undyed_non_mine_vars))
        else:
            model.Add(undyed_non_mine_sum == 0)

        # 枚举所有因子对 (a,b) 使得 a*b == self.count，且 0<=a,b<=8
        pairs = []
        for a in range(0, 9):
            for b in range(0, 9):
                if a * b == self.count:
                    pairs.append((a, b))

        if not pairs:
            # 没有因子对，则线索不可满足
            model.Add(False).OnlyEnforceIf(s)
            logger.trace(f"[NM] {self.pos}: no factor pairs for count={self.count}, unsat")
            return

        # 使用乘法约束：dyed_mine_sum * undyed_non_mine_sum == self.count
        product_var = model.NewIntVar(0, 64, f"nm_product_{self.pos.row}_{self.pos.col}")
        model.AddMultiplicationEquality(product_var, [dyed_mine_sum, undyed_non_mine_sum])
        model.Add(product_var == self.count).OnlyEnforceIf(s)
        # 同时保留 AddAllowedAssignments 作为额外约束
        model.AddAllowedAssignments([dyed_mine_sum, undyed_non_mine_sum], pairs).OnlyEnforceIf(s)

        logger.trace(f"[NM] {self.pos}: count={self.count}, allowed pairs={pairs}")
