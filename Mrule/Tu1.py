#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/20
# @Author  : Agent
# @FileName: Tu1.py
"""
[Tu1] 图棋1: 雷线索表示箭头方向最近的n个雷雷值为0。

规则详细说明:
1. 规则类别: 中线规则 (Mrule)。线索存储在雷格上，箭头标注在该雷格上。
2. 箭头方向: 可为单箭头、双箭头、三箭头或四箭头的任意组合。
   - 单箭头: ↑, ↓, ←, →
   - 双箭头: ↑↓, ↑→, ↑←, ↓→, ↓←, →←
   - 三箭头: ↑→↓, ↑↓←, ↑→←, ↓→←
   - 四箭头: ↓→↑←
3. 线索值 n: 线索格上的数字即为 n，表示沿箭头方向需要处理的雷的数量。
4. 雷值处理规则:
   - 沿每个箭头方向，从线索雷格出发，沿直线方向寻找最近的 n 个雷格。
   - 找到的这 n 个雷格（每个方向分别计算），其雷值变为 0。
   - 如果某个方向上的雷格总数不足 n 个，则只处理实际存在的那些雷格。
   - 线索雷格本身不包含在"最近的 n 个雷"中。
5. 与其他规则的交互: 本规则与 [V'] 规则配合使用，[V'] 通过命名空间 "tu1" 获取雷值变量。

使用方式:
    -c Tu1 V':tu1
"""

from typing import List, Dict, Tuple, Any, Optional

from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template, ValueTemplate
from minesweepervariants.utils.tool import get_logger, get_random

from ....abs.Mrule import AbstractMinesClueRule, AbstractMinesValue
from minesweepervariants.board import Board, Position


class RuleTu1(AbstractMinesClueRule):
    """[Tu1] 图棋1 规则类"""

    id = "Tu1"
    name = "Tu1"
    name.zh_CN = "图棋1"
    doc = "Mines clue indicates that the nearest n mines in the arrow direction have a mine value of 0."
    doc.zh_CN = "雷线索表示箭头方向最近的n个雷雷值为0。"
    tags = ["Creative", "Local", "Arrow Clue", "Mine-Value"]
    creation_time = "2026-07-20"
    author = ("小中医", 3086842243)

    def __init__(self, board: 'Board' = None, data: str = None):
        """
        初始化规则，注册特殊类型函数到命名空间 "tu1"。

        这样 [V'] 在 fill 阶段就可以通过 board.batch(..., special="tu1") 获取雷值。
        """
        super().__init__(board, data)
        if board is not None:
            # 注册类型特殊函数，让 [V'] 的 fill 方法能够获取默认雷值
            def tu1_type_func(b: Board, pos: Position) -> int:
                """返回指定位置的雷值（1 或 0）"""
                return 1 if b.get_type(pos) == 'F' else 0

            board.register_type_special("tu1", tu1_type_func)
            get_logger().trace("[Tu1] Registered type special function for namespace 'tu1'")

    def create_constraints(self, board: 'Board', switch):
        """
        重写规则类的create_constraints，先创建所有位置的雷值变量，
        并设置默认值（雷=1，非雷=0），
        然后调用父类遍历线索，线索层会根据条件将某些雷覆盖为0。
        """
        model = board.get_model()
        logger = get_logger()
        
        # 1. 创建所有位置的雷值变量，并设置默认值
        val_vars = {}
        bounds = board.boundary('main')
        if bounds is None:
            return
        for r in range(bounds.row + 1):
            for c in range(bounds.col + 1):
                p = Position(c, r, 'main')
                # 创建雷值变量
                val_var = model.NewBoolVar(f'tu1_val_{p.row}_{p.col}')
                mine_var = board.get_variable(p)
                # 默认值：非雷为0，雷为1
                model.Add(val_var == 0).OnlyEnforceIf(mine_var.Not())
                model.Add(val_var == 1).OnlyEnforceIf(mine_var)
                # 注册到 special 命名空间，供 [V'] 使用
                board.register_variable_special("tu1", p, val_var)
                val_vars[p] = val_var
        board._tu1_val_vars = val_vars
        logger.trace("[Tu1] Created tu1 variables for all positions with default values (mine=1, non-mine=0)")
        
        # 2. 调用父类，它会遍历所有雷并调用每个线索的create_constraints
        # 线索层会添加将某些雷设为0的约束，覆盖默认值1
        super().create_constraints(board, switch)
        logger.trace("[Tu1] Finished creating constraints for all clues.")

    def fill(self, board: 'Board') -> 'Board':
        """
        填充题板：遍历所有雷格，随机生成方向和 n，并创建线索值对象。
        同时为所有位置创建雷值变量并注册到命名空间 'tu1'，供 [V'] 使用。

        Args:
            board: 当前的题板对象

        Returns:
            Board: 填充后的题板
        """
        rng = get_random()
        logger = get_logger()

        # 为所有位置创建雷值变量并注册到 special 命名空间
        model = board.get_model()
        bounds = board.boundary('main')
        if bounds is not None:
            if not hasattr(board, '_tu1_val_vars'):
                board._tu1_val_vars = {}
            val_vars = board._tu1_val_vars
            for r in range(bounds.row + 1):
                for c in range(bounds.col + 1):
                    p = Position(c, r, 'main')
                    # 创建雷值变量
                    val_var = model.NewBoolVar(f'tu1_val_{p.row}_{p.col}')
                    mine_var = board.get_variable(p)
                    # 非雷必须为0
                    model.Add(val_var == 0).OnlyEnforceIf(mine_var.Not())
                    # 注册到 special 命名空间，供 [V'] 使用
                    board.register_variable_special("tu1", p, val_var)
                    val_vars[p] = val_var
            logger.trace(f"[Tu1] Created and registered tu1 variables for all positions")

        # 遍历所有雷格，生成线索
        for pos, _ in board("F"):
            # 随机生成方向组合: 位0-上，位1-下，位2-左，位3-右
            # 确保至少有一个方向
            directions = rng.choice([
                0b0001, 0b0010, 0b0100, 0b1000,           # 单箭头
                0b0011, 0b0101, 0b1001, 0b0110, 0b1010, 0b1100,  # 双箭头
                0b0111, 0b1011, 0b1101, 0b1110,           # 三箭头
                0b1111                                    # 四箭头
            ])
            # 数字 n: 1 到 3 之间的随机整数
            n = rng.randint(1, 3)

            # 创建线索值对象并存储
            clue = MinesValueTu1(pos, directions, n)
            board.set_value(pos, clue)

            logger.trace(f"[Tu1] Clue at {pos}: directions={directions:b}, n={n}")

        return board


class MinesValueTu1(AbstractMinesValue):
    """
    [Tu1] 图棋1 线索值类

    存储线索格上的方向组合和数字 n。
    """

    id = RuleTu1.id

    def __init__(self, pos: 'Position', directions: int = 0, n: int = 1):
        """
        初始化线索值。

        Args:
            pos: 线索格位置
            directions: 方向位掩码 (位0-上，位1-下，位2-左，位3-右)
            n: 数字 n，表示需要处理的雷的数量
        """
        self.pos = pos
        self.directions = directions
        self.n = n
        # 线索值本身存储为 SingleIntValue 占位符
        # 实际的方向和 n 存储在上面的属性中
        self.value = SingleIntValue(0, is_mine=False)

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        """
        从 JSON 数据恢复线索值对象。

        Args:
            pos: 线索格位置
            data: JSON 数据

        Returns:
            AbstractValue: 恢复的线索值对象
        """
        _data = deep_unwrap(data)

        if not isinstance(_data, dict):
            raise ValueError("Expected dict for Tu1 clue data")

        directions = _data.get('directions', 0)
        n = _data.get('n', 1)

        return cls(pos, directions, n)

    def json(self) -> dict:
        """
        返回 JSON 表示。

        Returns:
            dict: JSON 数据
        """
        return {
            'directions': self.directions,
            'n': self.n
        }

    def high_light(self, board: 'Board') -> list['Position']:
        """
        返回应高亮显示的位置列表。

        Args:
            board: 题板对象

        Returns:
            list[Position]: 高亮位置列表
        """
        highlight_positions = []
        direction_offsets = [(0, -1), (0, 1), (-1, 0), (1, 0)]

        for i, (dx, dy) in enumerate(direction_offsets):
            if self.directions & (1 << i):
                cur = self.pos
                while True:
                    cur = cur.shift(dx, dy)
                    if not board.in_bounds(cur):
                        break
                    highlight_positions.append(cur)

        return highlight_positions

    def create_constraints(self, board: 'Board', switch):
        """
        添加约束: 对于每个方向，最近的 n 个雷的雷值为 0。

        使用方式: -c Tu1 V':tu1

        Args:
            board: 题板对象
            switch: 开关对象，用于条件约束
        """
        model = board.get_model()
        s = switch.get(model, self)
        logger = get_logger()

        # 通过 board 的 special 机制获取雷值变量
        def get_tu1_var(p):
            var = board.get_variable(p, special="tu1")
            if var is None:
                # 如果变量不存在，创建并注册
                var = model.NewBoolVar(f'tu1_val_{p.row}_{p.col}')
                mine_var = board.get_variable(p)
                model.Add(var == 0).OnlyEnforceIf(mine_var.Not())
                model.Add(var == 1).OnlyEnforceIf(mine_var)
                board.register_variable_special("tu1", p, var)
                logger.warning(f"[Tu1] Created missing variable for {p} in MinesValueTu1")
            return var

        # 记录被 Tu1 覆盖（设为0）的位置
        covered = set()

        # 方向偏移
        direction_offsets = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        direction_names = ['up', 'down', 'left', 'right']

        # 对于每个方向
        for i, (dx, dy) in enumerate(direction_offsets):
            if not (self.directions & (1 << i)):
                continue

            # 获取该方向上的所有位置
            positions = []
            cur = self.pos
            while True:
                cur = cur.shift(dx, dy)
                if not board.in_bounds(cur):
                    break
                positions.append(cur)

            if not positions:
                continue

            # 创建累计雷数变量
            cum_vars = []
            for j, p in enumerate(positions):
                # 获取该位置的布尔变量（是否为雷）
                mine_var = board.get_variable(p)

                # 创建累计雷数变量
                cum_var = model.NewIntVar(0, len(positions), f'cum_{self.pos}_{direction_names[i]}_{j}')
                cum_vars.append(cum_var)

                # 添加累计雷数约束
                if j == 0:
                    model.Add(cum_var == mine_var)
                else:
                    model.Add(cum_var == cum_vars[j - 1] + mine_var)

                # 如果该位置是雷且累计雷数 <= n，则雷值为 0
                # 通过 board 的 special 机制获取雷值变量
                val_var = get_tu1_var(p)
                le_n_var = model.NewBoolVar(f'le_n_{self.pos}_{direction_names[i]}_{j}')
                model.Add(cum_var <= self.n).OnlyEnforceIf(le_n_var)
                model.Add(cum_var > self.n).OnlyEnforceIf(le_n_var.Not())
                # 如果该位置是雷且累计雷数 <= n，则雷值为 0
                model.Add(val_var == 0).OnlyEnforceIf([mine_var, le_n_var])
                # 记录该位置已被覆盖（设为0）
                covered.add(p)
                # 同时记录到 board 的全局覆盖集合中
                if not hasattr(board, '_tu1_covered'):
                    board._tu1_covered = set()
                board._tu1_covered.add(p)

            logger.trace(f"[Tu1] Added constraints for direction {direction_names[i]} at {self.pos}, n={self.n}")

        # 注意：默认值1由规则层统一添加，此处不再重复添加
        logger.trace(f"[Tu1] Added constraints for clue at {self.pos}, directions={self.directions:b}, n={self.n}")
