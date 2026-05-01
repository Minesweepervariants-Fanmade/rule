#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[AVG] 平均
作者: NT (2201963934)
最后编辑时间: 2026-04-10 00:00:00

规则拆分定义(验收基准):
1) 规则对象与适用范围:
  - 右线规则(Rrule), 作用对象为数字线索格/非雷格。
  - 规则语义按“已知答案盘”与“求解约束”两阶段一致处理。
  - 不属于雷布局规则, 不修改总雷数, 也不引入额外雷格类型。

2) 核心术语精确定义:
  - 基准线索值 b(p): 格 p 周围八格中的雷数量, 只统计题板内有效格, 越界格不计入。
  - 正交连通非雷分量 C: 在四邻接(上下左右)关系下, 由所有非雷格组成的最大连通分量。
  - 分量平均值 avg(C): C 内所有格的基准线索值之和除以 |C|, 结果保留为最简有理数。
  - 显示线索值 v(p): 若 p 属于分量 C, 则 v(p)=avg(C), 即同一正交连通非雷分量内所有格显示相同的平均值。

3) 计数对象、边界条件、越界处理:
  - 计数对象是每个非雷分量内的基准线索值之和与分量大小。
  - 四邻接用于分量划分, 八邻接用于基准线索值 b(p) 的计算。
  - 角格、边格按有效邻格参与计算; 越界位置不参与八邻或四邻统计。
  - 若分量中仅有 1 个格, 则其显示值等于自身的基准线索值。

4) fill 阶段语义与 create_constraints 阶段语义等价关系:
  - fill 阶段: 先按标准扫雷规则求出每个非雷格的 b(p), 再按四邻接非雷分量计算 avg(C), 将该分量内所有格统一写成同一个有理数显示值。
  - create_constraints 阶段: 约束求解结果中的每个非雷分量满足“同分量同值”且该值等于分量内 b(p) 的平均值。
  - 两阶段应对同一分量划分与同一平均定义保持一致, 不能在 fill 与约束之间引入不同的取整或截断语义。

5) 可验证样例:
  - 5x5 盘面若被雷分成两个正交连通非雷分量, 其中一个分量内基准线索值之和为 10、格数为 4, 则该分量所有格应显示 5/2。
  - 若另一个分量内基准线索值之和为 32、格数为 13, 则该分量所有格应显示 32/13。
  - 边角格的统计方式与中心格一致, 仅受有效邻格数量影响。

验收要点:
  - 规则展示文本应清晰体现“非雷分量求平均”的语义。
  - 盘面上同一正交连通非雷分量内的数字必须一致。
  - 输出中的分数必须为最简分数, 不得使用浮点近似。
"""

from collections import deque
from fractions import Fraction

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition
from ...rule.Lrule.connect import connect


_KEY_CACHE: dict[tuple[int, str], dict[str, object]] = {}


class RuleAVG(AbstractClueRule):
  id = "AVG"
  name = "Average"
  name.zh_CN = "平均"
  doc = "四联通非雷格的线索值求平均"

  @staticmethod
  def _neighbors4(pos: "AbstractPosition") -> list["AbstractPosition"]:
    return [pos.up(), pos.down(), pos.left(), pos.right()]

  @staticmethod
  def _valid_neighbors(board: "AbstractBoard", pos: "AbstractPosition") -> list["AbstractPosition"]:
    return [nei for nei in pos.neighbors(2) if board.in_bounds(nei)]

  @classmethod
  def _collect_component(
    cls,
    board: "AbstractBoard",
    start: "AbstractPosition",
  ) -> list["AbstractPosition"]:
    if board.get_type(start, special="raw") == "F":
      return []

    queue = deque([start])
    seen = {start}
    component: list[AbstractPosition] = []

    while queue:
      current = queue.popleft()
      component.append(current)
      for neighbor in cls._neighbors4(current):
        if neighbor in seen or not board.in_bounds(neighbor):
          continue
        if board.get_type(neighbor, special="raw") == "F":
          continue
        seen.add(neighbor)
        queue.append(neighbor)

    return component

  def fill(self, board: "AbstractBoard") -> "AbstractBoard":
    for key in board.get_interactive_keys():
      raw_positions = [pos for pos, _ in board("N", key=key, special="raw")]
      visited: set[AbstractPosition] = set()

      for start in raw_positions:
        if start in visited:
          continue

        component = self._collect_component(board, start)
        if not component:
          continue

        visited.update(component)
        total = 0
        for pos in component:
          neighbors = self._valid_neighbors(board, pos)
          total += sum(1 for nei in neighbors if board.get_type(nei, special="raw") == "F")

        avg = Fraction(total, len(component))
        for pos in component:
          board.set_value(pos, ValueAVG(pos, avg=avg))

    return board

  def create_constraints(self, board: "AbstractBoard", switch):
    model = board.get_model()
    s = switch.get(model, self)

    for key in board.get_interactive_keys():
      cache_key = (id(model), key)
      if cache_key not in _KEY_CACHE:
        _KEY_CACHE[cache_key] = self._build_key_cache(board, key, model, s)

      cache = _KEY_CACHE[cache_key]
      positions = cache["positions"]
      if not positions:
        continue

      pos_index = cache["pos_index"]
      component_ids = cache["component_ids"]
      raw_vars = cache["raw_vars"]
      count_vars = cache["count_vars"]

      for pos, obj in board("C", key=key, special="raw"):
        if not isinstance(obj, ValueAVG):
          continue

        raw_var = board.get_variable(pos, special="raw")
        if raw_var is not None:
          model.Add(raw_var == 0).OnlyEnforceIf(s)

        idx = pos_index.get(pos)
        if idx is None:
          continue

        anchor_component = component_ids[idx]
        same_component_vars = []
        weighted_count_vars = []

        for cell_idx, cell_raw in enumerate(raw_vars):
          if cell_raw is None:
            continue

          same_component = model.NewBoolVar(f"[AVG]same_{key}_{idx}_{cell_idx}")
          same_component_hit = model.NewBoolVar(f"[AVG]same_hit_{key}_{idx}_{cell_idx}")

          model.Add(component_ids[cell_idx] == anchor_component).OnlyEnforceIf([same_component_hit, s])
          model.Add(component_ids[cell_idx] != anchor_component).OnlyEnforceIf([same_component_hit.Not(), s])
          model.Add(same_component <= same_component_hit).OnlyEnforceIf(s)
          model.Add(same_component + cell_raw <= 1).OnlyEnforceIf(s)
          model.Add(same_component >= same_component_hit - cell_raw).OnlyEnforceIf(s)

          same_component_vars.append(same_component)

          weighted_count = model.NewIntVar(0, 8, f"[AVG]weighted_{key}_{idx}_{cell_idx}")
          model.Add(weighted_count == count_vars[cell_idx]).OnlyEnforceIf([same_component, s])
          model.Add(weighted_count == 0).OnlyEnforceIf([same_component.Not(), s])
          weighted_count_vars.append(weighted_count)

        if not same_component_vars:
          continue

        total_count = sum(weighted_count_vars)
        component_size = sum(same_component_vars)
        model.Add(obj.value.denominator * total_count == obj.value.numerator * component_size).OnlyEnforceIf(s)

  @staticmethod
  def _build_key_cache(
    board: "AbstractBoard",
    key: str,
    model,
    s,
  ) -> dict[str, object]:
    positions_vars = [
      (pos, var)
      for pos, var in board(key=key, mode="variable", special="raw")
      if var is not None
    ]
    positions = [pos for pos, _ in positions_vars]
    pos_index = {pos: idx for idx, pos in enumerate(positions)}
    raw_vars = [var for _, var in positions_vars]

    component_ids = connect(
      model=model,
      board=board,
      switch=s,
      component_num=None,
      ub=False,
      connect_value=0,
      nei_value=1,
      positions_vars=positions_vars,
      special="raw",
    )

    count_vars = []
    for pos in positions:
      neighbors = board.batch([nei for nei in pos.neighbors(2) if board.in_bounds(nei)], mode="variable", drop_none=True, special="raw")
      count_var = model.NewIntVar(0, len(neighbors), f"[AVG]count_{key}_{pos.x}_{pos.y}")
      model.Add(count_var == sum(neighbors)).OnlyEnforceIf(s)
      count_vars.append(count_var)

    return {
      "positions": positions,
      "pos_index": pos_index,
      "raw_vars": raw_vars,
      "component_ids": component_ids,
      "count_vars": count_vars,
    }


class ValueAVG(AbstractClueValue):
  def __init__(self, pos: "AbstractPosition", avg: Fraction | int | tuple[int, int] | None = None, code: bytes = None):
    super().__init__(pos, code)
    if code is not None:
      text = code.decode("ascii")
      if "/" in text:
        numerator, denominator = text.split("/", 1)
        self.value = Fraction(int(numerator), int(denominator))
      elif text:
        self.value = Fraction(int(text), 1)
      else:
        self.value = Fraction(0, 1)
    else:
      if avg is None:
        self.value = Fraction(0, 1)
      elif isinstance(avg, Fraction):
        self.value = avg
      elif isinstance(avg, tuple):
        self.value = Fraction(avg[0], avg[1])
      else:
        self.value = Fraction(int(avg), 1)

    self.neighbor4 = self._neighbors4(self.pos)

  @staticmethod
  def _neighbors4(pos: "AbstractPosition") -> list["AbstractPosition"]:
    return [pos.up(), pos.down(), pos.left(), pos.right()]

  def __repr__(self):
    if self.value.denominator == 1:
      return str(self.value.numerator)
    return f"{self.value.numerator}/{self.value.denominator}"

  @classmethod
  def type(cls) -> bytes:
    return RuleAVG.id.encode("ascii")

  def code(self) -> bytes:
    if self.value.denominator == 1:
      return str(self.value.numerator).encode("ascii")
    return f"{self.value.numerator}/{self.value.denominator}".encode("ascii")

  def high_light(self, board: "AbstractBoard") -> list["AbstractPosition"]:
    component = [self.pos]
    queue = deque([self.pos])
    seen = {self.pos}

    while queue:
      current = queue.popleft()
      for neighbor in self._neighbors4(current):
        if neighbor in seen or not board.in_bounds(neighbor):
          continue
        if board.get_type(neighbor, special="raw") == "F":
          continue
        seen.add(neighbor)
        queue.append(neighbor)
        component.append(neighbor)

    return component
