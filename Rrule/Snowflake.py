#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[$] Snowflake: Each row and column has exactly one "snowflake" clue.
A snowflake clue counts as Vanilla (standard 8-neighbor mines).
All other clues count according to the appended rule.

Usage: $:base_rule or $:base_rule;snow_rule
Example: $:1X  (snowflake = Vanilla, others = 1X)
         $:1X;V (explicit: snowflake = V, others = 1X)
"""

from typing import List, Optional, Tuple

from ....abs.Mrule import AbstractMinesValue
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition, MASTER_BOARD, Size
from ....utils.impl_obj import VALUE_QUESS, VALUE_CROSS
from ....utils.tool import get_random, get_logger
from ....impl.impl_obj import get_rule, get_value
from ..sharpRule.Csharp import FakeSwitch


NAME_SNOW = "$"
SPLIT_SNOW = "SNOW"


class RuleDollar(AbstractClueRule):
    id = "$"
    name = "Snowflake"
    name.zh_CN = "雪花"
    doc = ("Each row and column has exactly one 'snowflake' clue. A snowflake clue counts as Vanilla (standard "
           "8-neighbor mines). All other clues count according to the appended rule.")
    doc.zh_CN = "每行每列恰有一个'雪花'线索。雪花线索默认使用V线索。其他线索按附加规则计数。"
    tags = ["Creative", "Local", "Number Clue", "Construction"]
    creation_time = "2026-05-11"
    author = ("Boi", 0)

    def __init__(self, board: AbstractBoard = None, data: str = None):
        super().__init__(board, data)
        self.onrandom = False
        base_rule_name, base_rule_data = self._parse_rule_part(data, 0)
        snow_rule_name, snow_rule_data = self._parse_rule_part(data, 1)
        if snow_rule_name is None:
            snow_rule_name = "V"
            snow_rule_data = None
        if base_rule_name is None:
            raise ValueError("Snowflake rule requires a base rule")

        bound = board.boundary(MASTER_BOARD)
        if bound.x != bound.y:
            raise ValueError("Snowflake rule requires a square board")

        board.generate_board(NAME_SNOW, Size(bound.x + 1, bound.y + 1))

        self.base_rule = board.get_rule_instance(
            rule_name=base_rule_name,
            data=base_rule_data, add=False
        )
        self.snow_rule = board.get_rule_instance(
            rule_name=snow_rule_name,
            data=snow_rule_data, add=False
        )

    def _parse_rule_part(self, data: str, idx: int) -> Tuple[Optional[str], Optional[str]]:
        if not data:
            return None, None
        parts = data.split(";")
        if idx >= len(parts):
            return None, None
        part = parts[idx]
        from minesweepervariants.impl.summon.summon import CONFIG
        if CONFIG["delimiter"] in part:
            rule_id, rule_data = part.split(CONFIG["delimiter"], 1)
            return rule_id, rule_data
        return part, None

    def init_clear(self, board: 'AbstractBoard'):
        for pos, _ in board(key=NAME_SNOW):
            board[pos] = None

    def init_board(self, board: 'AbstractBoard'):
        for pos, _ in board("N", key=NAME_SNOW):
            board[pos] = VALUE_CROSS

    def fill(self, board: AbstractBoard) -> AbstractBoard:
        # 获取基础规则的 fill 结果
        base_board = board.clone()
        base_board = self.base_rule.fill(base_board)
        snow_board = board.clone()
        snow_board = self.snow_rule.fill(snow_board)

        # 遍历所有非雷格，填充线索
        for pos, _ in board("N", key=MASTER_BOARD):
            x, y = pos.x, pos.y
            snow_pos = board.get_pos(x, y, key=NAME_SNOW)
            is_snow = isinstance(board[snow_pos], AbstractMinesValue)
            snow_obj: AbstractClueValue = snow_board[pos]
            base_obj: AbstractClueValue = base_board[pos]
            # 创建 ValueDollar
            code = bytearray()
            code.extend(snow_obj.type())
            code.extend(SPLIT_SNOW.encode("ascii"))
            code.extend(base_obj.type())
            code.extend(SPLIT_SNOW.encode("ascii"))
            code.extend(snow_obj.code() if is_snow else base_obj.code())
            val = ValueDollar(pos, code=bytes(code))
            board.set_value(pos, val)
        return board

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        bound = board.boundary(key=NAME_SNOW)

        row = board.get_row_pos(bound)
        for pos in row:
            line = board.get_col_pos(pos)
            line_var = board.batch(line, mode="variable", drop_none=True)
            model.add(sum(line_var) == 1).OnlyEnforceIf(s)

        col = board.get_col_pos(bound)
        for pos in col:
            line = board.get_row_pos(pos)
            line_var = board.batch(line, mode="variable", drop_none=True)
            model.add(sum(line_var) == 1).OnlyEnforceIf(s)

        for pos, _ in board(key=NAME_SNOW):
            _pos = pos.clone()
            var = board.get_variable(pos)
            for key in board.get_interactive_keys():
                _pos.board_key = key
                key_var = board.get_variable(_pos)
                model.add(key_var == 0).OnlyEnforceIf([var, s])

        # random hint
        if self.onrandom:
            return
        self.onrandom = True
        random = get_random()
        perm = list(range(bound.x))
        random.shuffle(perm)
        random_list = []

        for x, y in enumerate(perm):
            pos = board.get_pos(x, y, key=NAME_SNOW)
            random_switch = model.new_bool_var("")
            model.add(board.get_variable(pos) == 1).OnlyEnforceIf(random_switch)
            random_list.append(random_switch)
        model.maximize(sum(random_list))


class ValueDollar(AbstractClueValue):
    def __init__(self, pos: AbstractPosition, code: Optional[bytes] = None):
        super().__init__(pos, code)
        parts = code.split(SPLIT_SNOW.encode("ascii"))
        self.base_rule = parts[0]
        self.snow_rule = parts[1]
        self.code_value = parts[2]

    def __repr__(self) -> str:
        return self.get_clue(self.base_rule, self.code_value).__repr__()

    @classmethod
    def type(cls) -> bytes:
        return b'$'

    def code(self) -> bytes:
        return SPLIT_SNOW.encode("ascii").join([self.base_rule, self.snow_rule, self.code_value])

    def high_light(self, board: AbstractBoard) -> List[AbstractPosition]:
        # 返回邻居区域（简化：高亮所有邻居，实际可能更复杂）
        snow_pos = board.get_pos(self.pos.x, self.pos.y, key=NAME_SNOW)
        is_snow = None if board[snow_pos] is None else isinstance(board[snow_pos], AbstractMinesValue)
        high_light = []
        if is_snow is not False:
            high_light.extend(self.get_clue(self.base_rule, self.code_value).high_light(board))
        if is_snow is not True:
            high_light.extend(self.get_clue(self.snow_rule, self.code_value).high_light(board))
        return high_light

    def get_clue(self, rule: bytes, value: bytes) -> Optional[AbstractClueValue]:
        clue_code = bytearray()
        try:
            clue_code.extend(rule)
            clue_code.extend(b'|')
            clue_code.extend(value)
            return get_value(self.pos, bytes(clue_code))
        except:
            return VALUE_QUESS

    def create_constraints(self, board: AbstractBoard, switch):
        # 实际约束由 RuleDollar.create_constraints 统一处理
        model = board.get_model()
        s = switch.get(model, self)

        snow_obj = self.get_clue(self.snow_rule, self.code_value)
        base_obj = self.get_clue(self.base_rule, self.code_value)

        snow_pos = board.get_pos(self.pos.x, self.pos.y, key=NAME_SNOW)
        snow_var = board.get_variable(snow_pos)
        select_snow = model.new_bool_var(f"select_snow_{self.pos}")
        select_base = model.new_bool_var(f"select_base_{self.pos}")

        model.add(select_snow == 0).OnlyEnforceIf(s.Not())
        model.add(select_base == 0).OnlyEnforceIf(s.Not())
        model.add(select_snow == 0).OnlyEnforceIf(s, snow_var)
        model.add(select_snow == 1).OnlyEnforceIf(s, snow_var.Not())
        model.add(select_base == 1).OnlyEnforceIf(s, snow_var)
        model.add(select_base == 0).OnlyEnforceIf(s, snow_var.Not())

        snow_obj.create_constraints(board, FakeSwitch(select_snow))
        base_obj.create_constraints(board, FakeSwitch(select_base))
