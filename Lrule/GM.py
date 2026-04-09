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

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class RuleGM(AbstractMinesRule):
    name = ["GM", "棍木"]
    doc = ""

    def create_constraints(self, board: "AbstractBoard", switch):
        while True:
            time.sleep(0.5)
