#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[CPV] 划分雷值
作者: NT (2201963934)
最后编辑时间: 2026-04-08 21:07:54

规则拆分定义(验收基准):
1) 规则对象与适用范围:
  - 右线规则(Rrule), 线索格语义基于“归属后”的周围八格雷数。
  - 计数对象为每个线索格周围八格中“归属于该线索格”的雷格(raw 语义下的 F)。
  - 额外引入“归属”语义: 每个格子最多归属一个其周围八邻中的线索格。

2) 核心术语精确定义:
  - 线索格 c: 当前盘面中带 CPV 线索值的格子。
  - 邻域 N8(c): 线索格 c 的周围八邻(仅题板内有效格)。
  - 归属变量 belong(p, c): 布尔变量, 表示格子 p 归属于线索格 c。
    定义域: 仅当 c 位于 p 的八邻域内(即 p ∈ N8(c))时该变量才允许存在。
  - 可归属线索集合 A(p): 所有满足“p ∈ N8(c)”的线索格 c 的集合。

3) 计数对象、边界条件、越界处理:
  - 线索计数按归属雷数: value(c) = sum_{p in N8(c)} [mine(p) and belong(p,c)]。
  - 归属唯一性: 对任意格 p, sum_{c in A(p)} belong(p, c) <= 1。
  - 必须归属条件: 若 A(p) 非空, 则 sum_{c in A(p)} belong(p, c) = 1。
  - 无可归属线索时(A(p) 为空)不强制归属。
  - 边格/角格按有效邻域处理, 越界位置不计入邻域与归属候选。

4) fill 阶段语义与 create_constraints 阶段语义等价关系:
  - fill 阶段: 先为每个格子在其候选线索中确定唯一归属(候选按坐标排序后取第一个),
    再以“归属到该线索的雷数”生成/刷新线索值。
  - create_constraints 阶段: 同时编码
    a) 线索值=八邻域内归属给该线索的雷数;
    b) 每个格子的归属唯一/必选(当存在候选线索格时)。
  - 以上约束共同定义 CPV 语义, 与 fill 阶段的归属计数语义保持一致。

5) 动态规则回调语义:
  - 该规则为动态规则, 当线索显隐增删时, 回调中必须基于“当前可见线索格”重建
    A(p) 的候选集合与归属约束作用域。
  - 已不可见(或被删除)的线索格不得继续参与 belong 候选。

6) 可验证样例:
  - 样例A: 3x3 盘面中心为线索格 c, 则其八邻格 p 均满足 A(p)={c}, 必须归属 c。
  - 样例B: 某格 p 同时邻接两个线索格 c1,c2, 则需满足 belong(p,c1)+belong(p,c2)=1。
  - 样例C: 某格 p 周围无任何线索格, 则不施加必须归属约束。

验收要点:
  - 不出现一个格子同时归属多个线索格的可行解。
  - 对于有候选线索格的格子, 不允许“未归属”的可行解。
  - 每个线索值必须等于其八邻域内“mine 且 belong 到该线索”的数量, 不是普通八邻雷数。
  - 动态显隐后, 归属候选集合与约束应与当前可见线索集合一致。
"""

from typing import TYPE_CHECKING

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition

if TYPE_CHECKING:
  from ortools.sat.python.cp_model import IntVar


class RuleCPV(AbstractClueRule):
  name = ["CPV", "划分雷值", "Clue Partition Value"]
  doc = "线索格表示周围八格雷数, 且每个格子在其可见候选线索集合中必须唯一归属。"

  dynamic_dig_enabled = True

  def __init__(self, board=None, data=None) -> None:
    super().__init__(board, data)
    self._visible_clue_positions: dict[str, set[tuple[int, int]]] = {}

  @staticmethod
  def _valid_neighbors(board: "AbstractBoard", pos: "AbstractPosition") -> list["AbstractPosition"]:
    return [nei for nei in pos.neighbors(2) if board.in_bounds(nei)]

  def _collect_visible_clues_from_board(self, board: "AbstractBoard") -> dict[str, set[tuple[int, int]]]:
    result: dict[str, set[tuple[int, int]]] = {}
    for key in board.get_interactive_keys():
      clues: set[tuple[int, int]] = set()
      for pos, obj in board(key=key):
        if isinstance(obj, ValueCPV):
          clues.add((pos.x, pos.y))
      result[key] = clues
    return result

  def _rebuild_visible_clues(
    self,
    board: "AbstractBoard",
    visibility_state: dict[str, dict[tuple[int, int], bool | None]],
  ) -> None:
    visible_map: dict[str, set[tuple[int, int]]] = {}
    for key in board.get_interactive_keys():
      visible: set[tuple[int, int]] = set()
      key_state = visibility_state.get(key, {})
      for (x, y), is_visible in key_state.items():
        if is_visible is not True:
          continue
        pos = board.get_pos(x, y, key)
        if pos is None:
          continue
        obj = board.get_value(pos)
        if isinstance(obj, ValueCPV):
          visible.add((x, y))
      visible_map[key] = visible
    self._visible_clue_positions = visible_map

  def dynamic_init_visibility(self, board, visibility_state):
    self._rebuild_visible_clues(board, visibility_state)

  def dynamic_on_visibility_changed(self, board, visibility_state, changed_positions):
    self._rebuild_visible_clues(board, visibility_state)

  def fill(self, board: "AbstractBoard") -> "AbstractBoard":
    for key in board.get_interactive_keys():
      clue_positions = sorted([(pos.x, pos.y) for pos, _ in board("N", key=key, special="raw")])
      clue_set = set(clue_positions)

      belong_target: dict[tuple[int, int], tuple[int, int]] = {}
      for pos, _ in board(key=key):
        candidates: list[tuple[int, int]] = []
        for nei in self._valid_neighbors(board, pos):
          clue_key = (nei.x, nei.y)
          if clue_key in clue_set:
            candidates.append(clue_key)
        if candidates:
          belong_target[(pos.x, pos.y)] = sorted(candidates)[0]

      clue_counts = {clue: 0 for clue in clue_positions}
      for pos, obj_type in board(mode="type", key=key, special="raw"):
        if obj_type != "F":
          continue
        target = belong_target.get((pos.x, pos.y))
        if target is not None:
          clue_counts[target] += 1

      for cx, cy in clue_positions:
        cpos = board.get_pos(cx, cy, key)
        if cpos is not None:
          board.set_value(cpos, ValueCPV(cpos, count=clue_counts[(cx, cy)]))
    return board

  def create_constraints(self, board: "AbstractBoard", switch):
    model = board.get_model()
    rule_switch = switch.get(model, self)

    visible_clues = self._visible_clue_positions
    if not visible_clues:
      visible_clues = self._collect_visible_clues_from_board(board)

    for key in board.get_interactive_keys():
      key_visible = visible_clues.get(key, set())
      if not key_visible:
        continue

      valid_visible_clues: dict[tuple[int, int], ValueCPV] = {}
      for cx, cy in key_visible:
        cpos = board.get_pos(cx, cy, key)
        if cpos is None:
          continue
        cobj = board.get_value(cpos)
        if isinstance(cobj, ValueCPV):
          valid_visible_clues[(cx, cy)] = cobj
      if not valid_visible_clues:
        continue

      clue_terms: dict[tuple[int, int], list[IntVar]] = {clue: [] for clue in valid_visible_clues}
      for pos, _ in board(key=key):
        if not board.in_bounds(pos):
          continue

        m = board.get_variable(pos, special="raw")
        if m is None:
          continue

        candidate_clues: list[tuple[int, int]] = []
        for nei in self._valid_neighbors(board, pos):
          clue_key = (nei.x, nei.y)
          if clue_key in valid_visible_clues:
            candidate_clues.append(clue_key)

        if not candidate_clues:
          continue

        belong_vars: list[IntVar] = []
        for cx, cy in candidate_clues:
          b = model.NewBoolVar(f"CPV_belong_{key}_{pos.x}_{pos.y}_{cx}_{cy}")
          t = model.NewBoolVar(f"CPV_mine_and_belong_{key}_{pos.x}_{pos.y}_{cx}_{cy}")

          model.Add(t <= m).OnlyEnforceIf(rule_switch)
          model.Add(t <= b).OnlyEnforceIf(rule_switch)
          model.Add(t >= m + b - 1).OnlyEnforceIf(rule_switch)

          belong_vars.append(b)
          clue_terms[(cx, cy)].append(t)

        model.Add(sum(belong_vars) <= 1).OnlyEnforceIf(rule_switch)
        model.Add(sum(belong_vars) == 1).OnlyEnforceIf(rule_switch)

      for clue_key, cobj in valid_visible_clues.items():
        model.Add(sum(clue_terms[clue_key]) == cobj.count).OnlyEnforceIf(rule_switch)


class ValueCPV(AbstractClueValue):
  def __init__(self, pos: "AbstractPosition", count: int = 0, code=None):
    super().__init__(pos, code if code is not None else b"")
    if code is not None:
      self.count = code[0]
    else:
      self.count = count
    self.neighbor = self.pos.neighbors(2)

  def __repr__(self):
    return str(self.count)

  @classmethod
  def type(cls) -> bytes:
    return RuleCPV.name[0].encode("ascii")

  def code(self) -> bytes:
    return bytes([self.count])

  def high_light(self, board: "AbstractBoard") -> list["AbstractPosition"]:
    return [nei for nei in self.neighbor if board.in_bounds(nei)]

  def create_constraints(self, board: "AbstractBoard", switch):
    return
