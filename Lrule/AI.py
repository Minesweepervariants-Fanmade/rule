#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[AI] 箭头: 所有格子显示八方向箭头, 雷分布满足沿箭头可不重补漏遍历。

规则拆分定义(验收基准):
1) 规则对象与范围:
  - 左线规则(Lrule), 约束对象是雷变量(raw), 不改格子类型。
  - 每个交互题板(key)独立建模, 不允许跨 key 链接。

2) 核心术语:
  - 箭头后继: 对位置 p, 沿固定方向得到 next(p)。
  - 入边: 形如 q->p 且 q,next(q)=p 的箭头边。
  - 不重补漏遍历: 雷格在同一 key 内构成一条有向哈密顿路径。

3) 计数对象与边界:
  - 仅统计当前 key 的交互格。
  - 越界 next(p) 记为无后继, 不产生边。
  - 无雷 key 合法, 此时不应强制存在根。

4) fill 与 create_constraints 等价语义:
  - fill 产生的雷分布必须满足: 每个有雷 key 恰有一个起点(root),
    非起点雷恰有一条入边, 雷编号连续且互异, 覆盖该 key 全部雷。
  - create_constraints 精确编码上述必要且充分条件。

5) 可验证样例:
  - 固定方向 value=6(向左) 时, 单 key 5x5 且 t=5 应可形成一行长度5链;
    不应因额外 key/跨 key 约束导致无解。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ....abs.Lrule import AbstractMinesRule
from ....utils.tool import get_random

if TYPE_CHECKING:
  from ....abs.board import AbstractBoard, AbstractPosition
  from ....impl.summon.solver import Switch


class RuleAI(AbstractMinesRule):
  name = ["AI", "箭头", "Arrow"]
  doc = "生成固定八方向箭头图, 雷格需沿箭头可不重补漏遍历"
  ARROWS = ["^", "^>", ">", "v>", "v", "v<", "<", "^<"]

  # 顺序: 上, 右上, 右, 右下, 下, 左下, 左, 左上
  DIRS = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]

  def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
    super().__init__(board, data)
    self.seed = 2201963934
    if data is not None:
      try:
        self.seed = int(data)
      except (TypeError, ValueError):
        pass
    self._dir_cache: dict[tuple[str, int, int], int] = {}
    if board is not None:
      self.onboard_init(board)

  def _populate_dir_cache(self, board: "AbstractBoard", key=None):
    random = get_random()
    keys = [key] if key is not None else sorted(board.get_board_keys(), key=lambda k: str(k))
    for board_key in keys:
      positions = sorted((pos for pos, _ in board(key=board_key)), key=lambda p: (p.x, p.y))
      for pos in positions:
        cache_key = (pos.board_key, pos.x, pos.y)
        if cache_key not in self._dir_cache:
          self._dir_cache[cache_key] = random.randint(0, 7)

  def _direction_index(self, pos: "AbstractPosition") -> int:
    key = (pos.board_key, pos.x, pos.y)
    if key not in self._dir_cache:
      # 缓存缺失时按同一稳定顺序补齐该 key, 避免显示/约束阶段漂移。
      board = self.board
      if board is not None:
        self._populate_dir_cache(board, key=pos.board_key)
      if key not in self._dir_cache:
        self._dir_cache[key] = get_random().randint(0, 7)
    return self._dir_cache[key]

  def _next_pos(self, board: "AbstractBoard", pos: "AbstractPosition"):
    direction = self._direction_index(pos)
    dx, dy = self.DIRS[direction]
    return board.get_pos(pos.x + dx, pos.y + dy, key=pos.board_key)

  def onboard_init(self, board: "AbstractBoard"):
    # 方向在初始化阶段一次性写入缓存, 显示与约束统一读取同一映射。
    self._populate_dir_cache(board)
    self._apply_pos_labels(board)

  def _apply_pos_labels(self, board: "AbstractBoard"):
    for key in board.get_board_keys():
      labels = {}
      for pos, _ in board(key=key):
        direction = self._direction_index(pos)
        labels[pos] = self.ARROWS[direction]
      board.set_config(key, "labels", labels)
      board.set_config(key, "pos_label", True)

  def init_board(self, board: "AbstractBoard"):
    # AI 是左线规则: 箭头方向通过 pos_label 显示, 不改格子对象类型。
    self._apply_pos_labels(board)

  def create_constraints(self, board: "AbstractBoard", switch: "Switch"):
    model = board.get_model()
    sw = switch.get(model, self)

    for key in board.get_interactive_keys():
      positions = [pos for pos, _ in board(key=key)]
      if not positions:
        continue

      size = len(positions)
      mines = {pos: board.get_variable(pos, special="raw") for pos in positions}
      ids = {
        pos: model.NewIntVar(0, size, f"AI_id_{key}_{pos.x}_{pos.y}")
        for pos in positions
      }
      roots = {
        pos: model.NewBoolVar(f"AI_root_{key}_{pos.x}_{pos.y}")
        for pos in positions
      }
      mine_count_key = model.NewIntVar(0, size, f"AI_mine_count_{key}")
      has_mine_key = model.NewBoolVar(f"AI_has_mine_{key}")
      root_count_key = model.NewIntVar(0, size, f"AI_root_count_{key}")

      model.Add(mine_count_key == sum(mines[pos] for pos in positions)).OnlyEnforceIf(sw)
      model.Add(mine_count_key >= 1).OnlyEnforceIf([sw, has_mine_key])
      model.Add(mine_count_key == 0).OnlyEnforceIf([sw, has_mine_key.Not()])

      pos_by_xy = {(pos.x, pos.y): pos for pos in positions}
      next_map: dict["AbstractPosition", "AbstractPosition | None"] = {}
      pred_map: dict["AbstractPosition", list["AbstractPosition"]] = {
        pos: [] for pos in positions
      }
      for pos in positions:
        direction = self._direction_index(pos)
        dx, dy = self.DIRS[direction]
        nxt = pos_by_xy.get((pos.x + dx, pos.y + dy))
        if nxt is not None and nxt in pred_map:
          next_map[pos] = nxt
          pred_map[nxt].append(pos)
        else:
          next_map[pos] = None

      edges: dict[tuple["AbstractPosition", "AbstractPosition"], object] = {}
      for src in positions:
        dst = next_map[src]
        if dst is None:
          continue
        edge = model.NewBoolVar(
          f"AI_edge_{key}_{src.x}_{src.y}_to_{dst.x}_{dst.y}"
        )
        edges[(src, dst)] = edge
        model.Add(edge <= mines[src]).OnlyEnforceIf(sw)
        model.Add(edge <= mines[dst]).OnlyEnforceIf(sw)
        model.Add(edge >= mines[src] + mines[dst] - 1).OnlyEnforceIf(sw)

      # id 编号: 非雷=0, 雷>0, root 雷且 id=1
      for pos in positions:
        model.Add(ids[pos] == 0).OnlyEnforceIf([sw, mines[pos].Not()])
        model.Add(ids[pos] > 0).OnlyEnforceIf([sw, mines[pos]])
        model.Add(roots[pos] <= mines[pos]).OnlyEnforceIf(sw)
        model.Add(ids[pos] == 1).OnlyEnforceIf([sw, roots[pos]])

      # 仅当该 key 有雷时才要求唯一 root; 无雷 key 允许 root=0
      model.Add(root_count_key == sum(roots[pos] for pos in positions)).OnlyEnforceIf(sw)
      model.Add(root_count_key == 1).OnlyEnforceIf([sw, has_mine_key])
      model.Add(root_count_key == 0).OnlyEnforceIf([sw, has_mine_key.Not()])

      # incoming(pos) 约束
      for pos in positions:
        incoming_edges = [
          edges[(src, pos)] for src in pred_map[pos] if (src, pos) in edges
        ]
        incoming = sum(incoming_edges) if incoming_edges else 0

        model.Add(incoming <= 1).OnlyEnforceIf(sw)
        model.Add(incoming == 0).OnlyEnforceIf([sw, roots[pos]])
        model.Add(incoming == 1).OnlyEnforceIf([sw, mines[pos], roots[pos].Not()])

      # 边激活时 id 严格递增
      for (src, dst), edge in edges.items():
        model.Add(ids[dst] == ids[src] + 1).OnlyEnforceIf([sw, edge])

      # 所有雷的 id 互异
      for i, pos1 in enumerate(positions):
        for pos2 in positions[i + 1:]:
          model.Add(ids[pos1] != ids[pos2]).OnlyEnforceIf([
            sw,
            mines[pos1],
            mines[pos2],
          ])
