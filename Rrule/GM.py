#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[GM] 棍木
作者: NT (2201963934)
最后编辑时间: 2026-04-09 10:19:12

规则拆分定义(验收基准):
1) 规则对象与适用范围:
  - 左线规则(Lrule)，仅对每个交互题板(key)的雷变量(raw)生效。
  - 不改格子类型，不涉及染色、题板分组或跨 key 联动。

2) 核心术语:
  - 棍木: 指 GM 规则在约束阶段的占位行为；其语义仅限定于 create_constraints 的执行过程。
  - 约束阶段: 规则被装载后，对当前 board 的每个交互 key 依次调用 create_constraints。

3) 计数对象、边界条件、越界处理:
  - 本规则不做任何空间计数，不统计行、列、斜线或邻域。
  - 边界与越界在规则语义中无参与项；任意尺寸棋盘均适用。

4) fill 阶段语义与 create_constraints 阶段语义:
  - 左线规则不实现 fill。
  - create_constraints 阶段仅保持 GM 的占位行为；当前约定为以 0.5 秒间隔持续等待，不向模型添加其他约束。

5) 可验证样例:
  - 5x5 单交互 key 棋盘启用 GM 后，调用 create_constraints 时应进入持续等待状态；棋盘显示与雷分布不被该规则改变。
"""

import time

from ....abs.Rrule import AbstractClueRule, ValueQuess
from minesweepervariants.board import Board
from ....abs.rule import AbstractValue
from ....utils.tool import get_random


class RuleGM(AbstractClueRule):
    id = "GM"
    name = "OttoMom"
    name.zh_CN = "棍木"
    doc = "Fill the board with some OttoMom"
    doc.zh_CN = "在题板上会有棍木"
    author = ("NT", 2201963934)
    tags = ["Creative", "WIP", "Local"]
    creation_time = "2026-04-09"

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        self.data = -1 if data is None else (int(data) if data else 0)

    def fill(self, board: 'Board') -> 'Board':
        for pos, _ in board("N"):
            board.set_value(pos, ValueGM(pos))
        return board

    def init_clear(self, board: 'Board'):
        if self.data > -1:
            positions = [pos for pos, obj in board("C") if isinstance(obj, ValueGM)]
            random = get_random()
            positions = random.sample(positions, k=len(positions) - self.data)
            for pos in positions:
                board.set_value(pos, None)


class ValueGM(ValueQuess):
    id = "GM"
    @classmethod
    def type(cls) -> bytes:
        return RuleGM.id.encode("ascii")

    def __repr__(self) -> str:
        return ""

    def weaker(self, board: Board) -> AbstractValue:
        return self

    def weaker_times(self) -> int:
        return 0

    def tag(self, board: 'Board') -> bytes:
        return b''
