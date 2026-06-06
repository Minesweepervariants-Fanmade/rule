#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/05/05
# @Author  : 雾 (3140864122)
# @FileName: RAND.py
"""
[RAND] 随机线索：线索是一个随机生成的数字

## 规则拆分定义

### 1. 规则对象与适用范围
- **规则类型**：Rrule（AbstractClueRule）
- **适用范围**：仅适用于线索格（N 类型）
- **约束阶段**：create_constraints 无约束（线索值与雷数无关）

### 2. 核心术语精确定义
- **随机线索值**：使用 `get_random().randint(range_min, range_max)` 生成的整数
- **range_min/range_max**：线索值的最小/最大范围，默认 0:8
- **data 格式**：`"range_min:range_max"`，如 `"0:8"`，默认 `"0:8"`

### 3. 计数对象、边界条件、越界处理
- 计数对象：无（不涉及雷数计数）
- 边界处理：随机值始终在 [range_min, range_max] 范围内
- 越界处理：不适用

### 4. fill 阶段语义
- 遍历 board("N") 所有线索格
- 使用 `get_random()` 获取随机数生成器
- 为每个格子生成范围 [range_min, range_max] 内的随机整数
- 创建 ValueRAND 对象并通过 board.set_value() 设置

### 5. create_constraints 阶段语义
- 无约束
- 因为线索值是随机生成的，与雷数分布无关
- 保留方法签名但实现为空

### 6. 可验证样例
- 5x5 棋盘，RAND 规则
- 填充后每个非雷格显示 0-8 之间的随机整数
- 验证：所有线索格的值都在指定范围内

## 使用方式
- `poetry run python -m minesweepervariants -s 5 -c RAND -a 1 --seed 42`
"""

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue
from minesweepervariants.board import JSONObject, Board, Position
from ....utils.tool import get_random


class RuleRAND(AbstractClueRule):
    id = "RAND"
    name = "Random"
    name.zh_CN = "随机线索"
    doc = "Clue is a randomly generated number"
    doc.zh_CN = "线索是一个随机生成的数字"
    tags = ["Variant", "Local", "Number Clue", "Fun"]
    creation_time = "2026-05-05"
    author = ("雾", 3140864122)

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        if data is None:
            self.range_min = 0
            self.range_max = 8
        else:
            try:
                parts = data.split(":")
                self.range_min = int(parts[0]) if len(parts) > 0 else 0
                self.range_max = int(parts[1]) if len(parts) > 1 else 8
            except (ValueError, IndexError):
                self.range_min = 0
                self.range_max = 8

    def fill(self, board: 'Board') -> 'Board':
        random = get_random()
        for pos, _ in board("N"):
            value = random.randint(self.range_min, self.range_max)
            board.set_value(pos, ValueRAND(pos, value))
        return board


class ValueRAND(AbstractClueValue):
    id = "RAND"
    def __init__(self, pos: 'Position', value: int = None, code: bytes = None):
        super().__init__(pos)
        if code is not None:
            self.value = code[0] if code else 0
        else:
            self.value = value if value is not None else 0

    def __repr__(self):
        return str(self.value)

    @classmethod
    def type(cls) -> bytes:
        return b"RAND"

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints(self, board: 'Board', switch):
        """
        无约束 - RAND 规则的线索值是随机生成的，与雷数无关
        """
        pass