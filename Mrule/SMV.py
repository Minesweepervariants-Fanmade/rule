#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/04/07
# @Author  : NT (2201963934)
# @FileName: SMV.py
"""
[SMV] 对称雷值

规则拆分定义（验收基线）
1) 规则对象与适用范围
- 规则对象: 雷线索规则（Mrule）。
- 赋值对象: 仅对题板上类型为 "F" 的雷格生成线索值。
- 求解约束对象: 线索值约束统计的是“题板上的雷变量”（即可求解变量为雷的格子）。

2) 核心术语定义
- 雷区（Mine Region）:
  由四联通（上、下、左、右）关系连成的、全部为雷格("F")的极大连通块。
- 所在雷区:
  某个雷线索格 p 所属的那一个四联通雷区。
- 最小覆盖矩形（MBR）:
  覆盖该雷区全部格子的轴对齐最小矩形。
  设行范围 [r_min, r_max]，列范围 [c_min, c_max]。
- 旋转中心（中心对称中心）:
  MBR 的几何中心，坐标为
    cr = (r_min + r_max) / 2
    cc = (c_min + c_max) / 2
  允许出现半整数（例如 2.5）。
- 中心对称映射:
  对雷区内任一格 (r, c)，其中心对称点定义为
    (r', c') = (2*cr - r, 2*cc - c)
  将该点映射到“题板坐标系”后，若落在棋盘内则纳入统计候选。
- 对称范围:
  所在雷区全部格子经上述中心对称映射后得到的目标坐标集合（去重后）。

3) 计数对象、边界条件与越界处理
- 计数对象: 对称范围中“在棋盘内且为雷”的格子数量。
- 去重规则: 若不同源格映射到同一目标坐标，只计 1 次（集合语义）。
- 越界处理: 映射目标坐标不在棋盘内则忽略，不计入范围与计数。
- 非整数坐标处理:
  若映射后坐标不是整数网格点，则该目标无有效格子，忽略。
  （等价地说，仅当 r'、c' 均为整数且在边界内时才作为有效目标格。）

4) fill 与 create_constraints 的语义等价
- fill 阶段:
  在完整答案板（已知所有雷）上，针对每个雷格 p:
  a. 找到 p 所在雷区 R。
  b. 基于 R 的 MBR 中心对 R 做中心对称映射，得到有效目标集合 S。
  c. 线索值 v(p) = |{ q in S : q 为雷 }|。
- create_constraints 阶段（关键修正）:
  求解时未知“p 所在雷区”的真实形状，不能直接使用单个已知 S。
  必须在局部候选空间内枚举所有可能雷区形状 R_i（均需满足: 包含 p、四联通、由雷组成），
  并为每个候选形状计算其对应的对称目标集合 S_i 与计数约束：
    sum( is_mine(q) for q in S_i ) == v(p)
  再通过布尔选择变量表达“至少一种候选成立”（必要时可再加互斥或一致性约束），
  使整体语义与 fill 的“真实雷区对应计数”一致。
  换言之，约束层面是“候选形状析取（OR）建模”，而非“已知形状直接代入”。

5) 可验证样例（文字）
- 样例A（最小 2 连块）:
  雷区 R = {(1,1),(1,2)}。
  MBR: r in [1,1], c in [1,2]，中心 (1,1.5)。
  映射: (1,1)->(1,2), (1,2)->(1,1)，对称范围 S 仍为 {(1,1),(1,2)}。
  因此该雷区内两个雷格的线索值均应等于 S 内实际雷数（该例为 2）。
- 样例B（越界）:
  若雷区靠边导致某些映射点落到棋盘外，这些点应被忽略，线索值只统计仍在棋盘内的映射目标。

6) 验收快检标准
- 同一个四联通雷区内的所有雷线索值应当相同。
  （因为它们共享同一个“所在雷区”定义，因此对称范围与计数目标一致。）

实现约束
- 规则逻辑实现由“规则实现代理”完成。
"""

from collections import deque
from typing import Optional

from ....abs.Mrule import AbstractMinesClueRule, AbstractMinesValue
from ....abs.board import AbstractBoard, AbstractPosition


class RuleSMV(AbstractMinesClueRule):
  name = ["SMV"]
  doc = "对称雷值: 雷线索表示所在雷区中心对称范围内的雷数"

  def __init__(self, board: "AbstractBoard" = None, data=None) -> None:  # type: ignore[assignment]
    super().__init__(board, data)
    # 可通过 data 微调候选枚举规模，避免组合爆炸。
    self.window_radius = 2
    self.max_shape_cells = 12
    self.max_candidates = 2400
    if isinstance(data, dict):
      self.window_radius = int(data.get("window_radius", self.window_radius))
      self.max_shape_cells = int(data.get("max_shape_cells", self.max_shape_cells))
      self.max_candidates = int(data.get("max_candidates", self.max_candidates))
    elif isinstance(data, (list, tuple)):
      if len(data) > 0:
        self.window_radius = int(data[0])
      if len(data) > 1:
        self.max_shape_cells = int(data[1])
      if len(data) > 2:
        self.max_candidates = int(data[2])
    elif isinstance(data, int):
      self.window_radius = int(data)

    self.window_radius = max(1, self.window_radius)
    self.max_shape_cells = max(1, self.max_shape_cells)
    self.max_candidates = max(1, self.max_candidates)

  @staticmethod
  def _neighbors4(board: "AbstractBoard", pos: "AbstractPosition") -> list["AbstractPosition"]:
    res = []
    for nxt in [pos.up(), pos.down(), pos.left(), pos.right()]:
      if board.in_bounds(nxt):
        res.append(nxt)
    return res

  @classmethod
  def _collect_region_by_type(
      cls,
      board: "AbstractBoard",
      start: "AbstractPosition",
      target_type: str = "F"
  ) -> set["AbstractPosition"]:
    if board.get_type(start) != target_type:
      return set()
    q = deque([start])
    vis = {start}
    while q:
      cur = q.popleft()
      for nxt in cls._neighbors4(board, cur):
        if nxt in vis:
          continue
        if board.get_type(nxt) != target_type:
          continue
        vis.add(nxt)
        q.append(nxt)
    return vis

  @staticmethod
  def _symmetric_targets(
      board: "AbstractBoard",
      region: set["AbstractPosition"]
  ) -> set["AbstractPosition"]:
    if not region:
      return set()
    xs = [p.x for p in region]
    ys = [p.y for p in region]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    board_key = next(iter(region)).board_key

    targets = set()
    for p in region:
      x2 = x_min + x_max - p.x
      y2 = y_min + y_max - p.y
      q = board.get_pos(x2, y2, board_key)
      if q is not None and board.in_bounds(q):
        targets.add(q)
    return targets

  @staticmethod
  def _window_positions(
      board: "AbstractBoard",
      center: "AbstractPosition",
      radius: int
  ) -> list["AbstractPosition"]:
    out = []
    for dx in range(-radius, radius + 1):
      for dy in range(-radius, radius + 1):
        pos = board.get_pos(center.x + dx, center.y + dy, center.board_key)
        if pos is not None and board.in_bounds(pos):
          out.append(pos)
    return out

  @classmethod
  def _enumerate_connected_candidates(
      cls,
      board: "AbstractBoard",
      anchor: "AbstractPosition",
      window: list["AbstractPosition"],
      max_cells: int,
      max_candidates: int
  ) -> list[set["AbstractPosition"]]:
    window_set = set(window)
    if anchor not in window_set:
      return []

    queue = deque([frozenset([anchor])])
    visited = {frozenset([anchor])}
    candidates: list[set["AbstractPosition"]] = []
    # 为避免 BFS 只在小形状层被截断，优先向深层扩展并在末端按规模筛选。
    expand_limit = max(max_candidates * 12, max_candidates)

    while queue and len(visited) <= expand_limit:
      subset = queue.pop()
      candidates.append(set(subset))
      if len(subset) >= max_cells:
        continue

      frontier = set()
      for p in subset:
        for nxt in cls._neighbors4(board, p):
          if nxt in window_set and nxt not in subset:
            frontier.add(nxt)

      for nxt in sorted(frontier, key=lambda pos: (pos.y, pos.x, pos.board_key)):
        new_subset = frozenset(set(subset) | {nxt})
        if new_subset in visited:
          continue
        visited.add(new_subset)
        queue.append(new_subset)

    if len(candidates) > max_candidates:
      bucket: dict[int, list[set["AbstractPosition"]]] = {}
      for region in candidates:
        bucket.setdefault(len(region), []).append(region)

      for size in bucket:
        bucket[size] = sorted(
          bucket[size],
          key=lambda region: tuple(sorted((p.y, p.x, p.board_key) for p in region))
        )

      sizes = sorted(bucket.keys(), reverse=True)
      selected: list[set["AbstractPosition"]] = []
      changed = True
      while changed and len(selected) < max_candidates:
        changed = False
        for size in sizes:
          if not bucket[size]:
            continue
          selected.append(bucket[size].pop(0))
          changed = True
          if len(selected) >= max_candidates:
            break
      candidates = selected

    return candidates

  @classmethod
  def _local_boundary(
      cls,
      board: "AbstractBoard",
      region: set["AbstractPosition"],
      window_set: set["AbstractPosition"]
  ) -> set["AbstractPosition"]:
    boundary = set()
    for p in region:
      for nxt in cls._neighbors4(board, p):
        if nxt in window_set and nxt not in region:
          boundary.add(nxt)
    return boundary

  def fill(self, board: "AbstractBoard") -> "AbstractBoard":
    for key in board.get_interactive_keys():
      comp_map: dict[AbstractPosition, set[AbstractPosition]] = {}
      for pos, _ in board("F", key=key):
        if pos in comp_map:
          continue
        region = self._collect_region_by_type(board, pos, "F")
        for rp in region:
          comp_map[rp] = region

      for pos, _ in board("F", key=key):
        region = comp_map.get(pos, {pos})
        targets = self._symmetric_targets(board, region)
        value = sum(1 for q in targets if board.get_type(q) == "F")
        board.set_value(pos, ValueSMV(pos, value.to_bytes(2, "big")))
    return board


class ValueSMV(AbstractMinesValue):
  def __init__(self, pos: "AbstractPosition", code: Optional[bytes] = None):
    self.pos = pos
    if code is None:
      self.value = 0
    elif len(code) == 1:
      self.value = code[0]
    else:
      self.value = int.from_bytes(code[:2], "big")

  def __repr__(self):  # type: ignore[override]
    return str(self.value)

  def code(self) -> bytes:
    return int(self.value).to_bytes(2, "big")

  @classmethod
  def type(cls) -> bytes:
    return RuleSMV.name[0].encode("ascii")

  def weaker(self, board: "AbstractBoard"):
    return self

  def weaker_times(self):
    return 0

  def create_constraints(self, board: "AbstractBoard", switch):
    model = board.get_model()
    s = switch.get(model, self)
    self_var = board.get_variable(self.pos)
    if self_var is not None:
      model.Add(self_var == 1).OnlyEnforceIf(s)

    rule = board.get_rule_instance(RuleSMV.name[0], add=False)
    if not isinstance(rule, RuleSMV):
      # 兜底默认值，保证在规则实例不可取时仍可运行。
      window_radius = 2
      max_shape_cells = 12
      max_candidates = 2400
    else:
      window_radius = rule.window_radius
      max_shape_cells = rule.max_shape_cells
      max_candidates = rule.max_candidates

    effective_radius = max(window_radius, min(4, self.value))
    window = RuleSMV._window_positions(board, self.pos, effective_radius)
    window_set = set(window)
    effective_max_cells = max(max_shape_cells, self.value)
    effective_max_cells = min(effective_max_cells, len(window_set))

    if self.value > len(window_set):
      model.Add(0 == 1).OnlyEnforceIf(s)
      return

    candidates = RuleSMV._enumerate_connected_candidates(
      board=board,
      anchor=self.pos,
      window=window,
      max_cells=effective_max_cells,
      max_candidates=max_candidates
    )

    # 同值连通提示候选: 作为枚举补充，降低真实形状被截断遗漏的概率。
    same_value_cells = {
      p for p in window
      if isinstance(board.get_value(p), ValueSMV) and board.get_value(p).value == self.value
    }
    hint_region: Optional[set[AbstractPosition]] = None
    if self.pos in same_value_cells:
      q = deque([self.pos])
      vis = {self.pos}
      while q:
        cur = q.popleft()
        for nxt in RuleSMV._neighbors4(board, cur):
          if nxt in same_value_cells and nxt not in vis:
            vis.add(nxt)
            q.append(nxt)
      if self.value <= len(vis) <= effective_max_cells:
        hint_region = set(vis)
        key = frozenset(vis)
        if all(frozenset(region) != key for region in candidates):
          candidates.append(set(vis))

    if hint_region is not None:
      candidates = [region for region in candidates if hint_region.issubset(region)]

    valid_candidates = []
    for region in candidates:
      has_conflict = False
      for p in region:
        p_value = board.get_value(p)
        if isinstance(p_value, ValueSMV) and p_value.value != self.value:
          has_conflict = True
          break
      if not has_conflict:
        valid_candidates.append(region)
    candidates = valid_candidates

    candidates = [region for region in candidates if len(region) >= self.value]

    if not candidates:
      model.Add(0 == 1).OnlyEnforceIf(s)
      return

    # 局部一致性剪枝:
    # 1) 四邻同值 SMV 线索需同雷状态；2) 四邻异值 SMV 线索不可同时为雷。
    if self_var is not None:
      for n in RuleSMV._neighbors4(board, self.pos):
        n_var = board.get_variable(n)
        if n_var is None:
          continue
        n_value = board.get_value(n)
        if isinstance(n_value, ValueSMV):
          if n_value.value == self.value:
            model.Add(self_var == n_var).OnlyEnforceIf(s)
          else:
            model.Add(self_var + n_var <= 1).OnlyEnforceIf(s)

    candidate_flags = []
    for idx, region in enumerate(candidates):
      t = model.NewBoolVar(f"SMV_cand_{self.pos}_{idx}")
      candidate_flags.append(t)

      # 候选雷区内部都必须是雷。
      for p in region:
        v = board.get_variable(p)
        if v is not None:
          model.Add(v == 1).OnlyEnforceIf([t, s])

      # 候选雷区在窗口内的四邻边界必须为非雷，避免把真实雷区的子块当作候选。
      boundary = RuleSMV._local_boundary(board, region, window_set)
      for p in boundary:
        v = board.get_variable(p)
        if v is not None:
          model.Add(v == 0).OnlyEnforceIf([t, s])

      targets = RuleSMV._symmetric_targets(board, region)
      target_vars = [board.get_variable(p) for p in targets]
      target_vars = [v for v in target_vars if v is not None]
      if target_vars:
        model.Add(sum(target_vars) == self.value).OnlyEnforceIf([t, s])
      else:
        model.Add(self.value == 0).OnlyEnforceIf([t, s])

    # 候选析取需要互斥，否则会把多个候选约束同时压到同一题板上。
    model.Add(sum(candidate_flags) == 1).OnlyEnforceIf(s)
