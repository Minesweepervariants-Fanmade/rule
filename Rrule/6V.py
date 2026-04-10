#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[6V] 经典扫雷(反相)
作者: NT (2201963934)
最后编辑时间: 2026-04-09 17:17:01

规则拆分定义(验收基准):
1) 规则对象与适用范围:
  - 右线规则(Rrule), 线索对象仍为数字线索。
  - 盘面显示侧: 仅影响线索是否显示与其数值展示。
  - 约束侧: 除常规线索约束外, 增加对非线索格(类型 N)的反相蕴含约束。

2) 核心术语精确定义:
  - 已给线索格: 当前盘面中可见且对象为数字线索的格。
  - 线索值集合 A: 所有已给线索格数值构成的集合(去重后)。
  - 邻域雷数 c(p): 格 p 周围八格 raw 雷变量之和。
    - 动态显示变量 show(p): 动态删线索阶段中, 线索格 p 的显示布尔变量。
    - 同值同显约束: 若两个线索格 p、q 的线索值相同, 则必须满足 show(p)=show(q)。

3) 计数对象、边界条件、越界处理:
  - 邻域固定为周围八格, 越界格不参与计数。
  - 仅对非线索格 p 施加 6V 反相约束。
  - 角格、边格按有效邻域计数, 语义与中心格一致。

4) fill 阶段语义与 create_constraints 阶段语义等价关系:
  - fill 阶段: 以当前规则生成/保留数字线索对象。
  - create_constraints 阶段: 对每个非线索格 p, 若 c(p) 命中 A, 则 p 必须为雷。
    即: c(p) ∈ A => mine(p)=1。
  - 上述为单向蕴含, 不要求 mine(p)=1 反推 c(p)∈A。
    - 动态删线索中的同值同显约束仅限制 show(p) 的取值关系, 不改变上述 6V 核心蕴含语义。

5) 可验证样例:
  - 5x5 盘面, 已给线索值集合 A={1,3}。
  - 对某非线索格 p, 若 c(p)=1 或 c(p)=3, 则 p 必须为雷。
  - 对某非线索格 q, 若 c(q)=2, 则 6V 不额外强制 q 为雷。
"""

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition


class Rule6V(AbstractClueRule):
    name = ["6V", "经典扫雷(全标)", "Vanilla(All Given)"]
    doc = "盘面上的数字线索标识周围八格的雷数。盘面上所有已给出的数字均已给出。其他格子不可能再出现已经给出的数字。"

    dynamic_dig_enabled = True
    dynamic_dig_use_visibility_optimizer = True

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        self._visible_clue_values: set[int] = set()

    @staticmethod
    def _valid_neighbors(board: "AbstractBoard", pos: "AbstractPosition") -> list["AbstractPosition"]:
        return [nei for nei in pos.neighbors(2) if board.in_bounds(nei)]

    @staticmethod
    def _collect_visible_values_from_board(board: "AbstractBoard") -> set[int]:
        values: set[int] = set()
        for key in board.get_interactive_keys():
            for _, obj in board(key=key):
                if isinstance(obj, Value6V):
                    values.add(obj.count)
        return values

    def _rebuild_visible_values(
        self,
        board: "AbstractBoard",
        visibility_state: dict[str, dict[tuple[int, int], bool | None]],
    ) -> None:
        values: set[int] = set()
        for key in board.get_interactive_keys():
            key_state = visibility_state.get(key, {})
            for (x, y), visible in key_state.items():
                if visible is not True:
                    continue
                pos = board.get_pos(x, y, key)
                obj = board.get_value(pos)
                if isinstance(obj, Value6V):
                    values.add(obj.count)
        self._visible_clue_values = values

    def dynamic_init_visibility(self, board, visibility_state):
        self._rebuild_visible_values(board, visibility_state)

    def dynamic_on_visibility_changed(self, board, visibility_state, changed_positions):
        self._rebuild_visible_values(board, visibility_state)

    def fill(self, board: "AbstractBoard") -> "AbstractBoard":
        for key in board.get_interactive_keys():
            for pos, _ in board("N", key=key, special="raw"):
                neighbors = self._valid_neighbors(board, pos)
                mine_count = board.batch(neighbors, mode="type", special="raw").count("F")
                board.set_value(pos, Value6V(pos, count=mine_count))
        return board

    def create_constraints(self, board: "AbstractBoard", switch):
        model = board.get_model()
        s = switch.get(model, self)

        clue_values = set(self._visible_clue_values)
        if not clue_values:
            clue_values = self._collect_visible_values_from_board(board)
        if not clue_values:
            return

        for key in board.get_interactive_keys():
            for pos, _ in board("N", key=key):
                neighbors = self._valid_neighbors(board, pos)
                neighbor_vars = board.batch(neighbors, mode="variable", drop_none=True, special="raw")
                max_count = len(neighbor_vars)
                count_var = model.NewIntVar(0, max_count, f"6V_count_{key}_{pos.x}_{pos.y}")
                model.Add(count_var == sum(neighbor_vars)).OnlyEnforceIf(s)

                mine_var = board.get_variable(pos, special="raw")
                for clue_value in clue_values:
                    if clue_value < 0 or clue_value > max_count:
                        continue
                    hit = model.NewBoolVar(f"6V_hit_{key}_{pos.x}_{pos.y}_{clue_value}")
                    model.Add(count_var == clue_value).OnlyEnforceIf([hit, s])
                    model.Add(count_var != clue_value).OnlyEnforceIf([hit.Not(), s])
                    model.Add(mine_var == 1).OnlyEnforceIf([hit, s])


class Value6V(AbstractClueValue):
    def __init__(self, pos: "AbstractPosition", count: int = 0, code: bytes = None):
        super().__init__(pos, code)
        if code is not None:
            self.count = code[0]
        else:
            self.count = count
        self.neighbor = self.pos.neighbors(2)

    def __repr__(self):
        return str(self.count)

    @classmethod
    def type(cls) -> bytes:
        return Rule6V.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.count])

    def high_light(self, board: "AbstractBoard") -> list["AbstractPosition"]:
        return [nei for nei in self.neighbor if board.in_bounds(nei)]

    def create_constraints(self, board: "AbstractBoard", switch):
        model = board.get_model()
        s = switch.get(model, self.pos)

        neighbors = [nei for nei in self.neighbor if board.in_bounds(nei)]
        neighbor_vars = board.batch(neighbors, mode="variable", drop_none=True, special="raw")
        model.Add(sum(neighbor_vars) == self.count).OnlyEnforceIf(s)
