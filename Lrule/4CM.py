#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/10/13 03:48
# @Author  : DeepSeek Agent
# @FileName: 4CM.py
"""
[4CM]康威多雷: 周围八格有2或3个雷的雷值翻倍。换句话说，按当前雷排布演化一次，若存活则雷值翻倍。
"""
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.solver import Switch


class Rule4CM(AbstractMinesRule):
    id = "4CM"
    name = "Conway Multiple"
    name.zh_CN = "康威多雷"
    doc = (
        "A mine whose 8 surrounding cells contain 2 or 3 mines has its "
        "mine value doubled. Equivalently, evolve the board once by Conway's "
        "Game of Life rule; if the mine survives, its value is doubled."
    )
    doc.zh_CN = (
        "周围八格有2或3个雷的雷值翻倍。换句话说，按当前雷排布演化一次，"
        "若存活则雷值翻倍。"
    )
    author = ("NT", 2201963934)
    tags = ["Variant", "Local", "Mine-Value"]
    creation_time = "2026-10-13"
    lib_only = True

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        self.onboard_init(board)
        self.rule = data or "raw"

    def onboard_init(self, board: 'Board'):
        def get_type(board: 'Board', pos: 'Position', *args, **kwargs):
            # 读取依赖命名空间下的雷值（默认 raw）
            value = board.get_type(pos, special=self.rule)

            if self.rule == 'raw':
                is_mine = value == 'F'
            else:
                is_mine = int(value) != 0

            if not is_mine:
                return 0

            # 统计周围八格中雷的数量（按 raw 语义统计）
            count = 0
            for nei in pos.neighbors(2):
                if not board.in_bounds(nei):
                    continue
                if board.get_type(nei, special='raw') == 'F':
                    count += 1

            # 康威生命游戏: 周围2或3个雷则存活 -> 雷值翻倍
            if count == 2 or count == 3:
                return 2
            return 1

        board.register_type_special('4CM', get_type)

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)
        for key in board.get_interactive_keys():
            for pos, _ in board(key=key):
                mine = board.get_variable(pos, special="raw")
                raw = board.get_variable(pos, special=self.rule)
                det = board.get_variable(pos, special='4CM')

                # 统计周围八格雷变量之和（基于 raw 雷变量）
                nei_vars = []
                for nei in pos.neighbors(2):
                    if not board.in_bounds(nei):
                        continue
                    v = board.get_variable(nei, special="raw")
                    if v is not None:
                        nei_vars.append(v)
                nei_sum = sum(nei_vars) if nei_vars else 0

                # 判断周围雷数是否为 2 或 3
                b2 = model.new_bool_var(f"4CM_eq2_{key}_{pos.col}_{pos.row}")
                b3 = model.new_bool_var(f"4CM_eq3_{key}_{pos.col}_{pos.row}")
                model.add(nei_sum == 2).only_enforce_if(b2)
                model.add(nei_sum != 2).only_enforce_if(b2.Not())
                model.add(nei_sum == 3).only_enforce_if(b3)
                model.add(nei_sum != 3).only_enforce_if(b3.Not())

                is_23 = model.new_bool_var(f"4CM_23_{key}_{pos.col}_{pos.row}")
                model.add_bool_or([b2, b3]).only_enforce_if(is_23)
                model.add_bool_and([b2.Not(), b3.Not()]).only_enforce_if(is_23.Not())

                # 非雷: det = 0
                model.add(det == 0).only_enforce_if(mine.Not())
                # 雷且周围2或3: det = 2 * raw（默认为2）
                model.add(det == raw * 2).only_enforce_if(mine, is_23)
                # 雷且周围非2非3: det = raw（默认为1）
                model.add(det == raw).only_enforce_if(mine, is_23.Not())

    def get_deps(self) -> list[str]:
        if self.rule == 'raw':
            return []
        return [self.rule]
