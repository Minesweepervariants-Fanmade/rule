#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[PUZ] 拼图: 同一 key 内的四联通雷块可各自平移，且所有平移后的雷块恰好拼成一个无重叠轴对齐矩形。

规则拆分定义(验收基准):
1) 规则对象与适用范围:
  - 左线规则(Lrule), 约束对象是每个交互 key 内的雷变量(raw)。
  - 仅在同一 key 内进行约束; 不允许跨 key 组合拼图。

2) 核心术语精确定义:
  - 四联通雷块: 当前 key 下按上下左右相邻划分得到的极大四连通雷格连通块。
  - 组件平移: 每个四联通雷块可各自选择一个平移向量 (dx, dy), 仅允许平移, 不允许旋转或镜像。
  - 可拼成矩形: 存在一组对每个四联通雷块的平移, 使所有平移后的雷块两两不重叠, 且它们的并集恰好等于一个轴对齐矩形的全体格点集合。
  - 轴对齐矩形 R: 存在整数 xmin<=xmax, ymin<=ymax, 使 R={ (x,y) | xmin<=x<=xmax 且 ymin<=y<=ymax }。

3) 计数对象、边界条件、越界处理:
  - 计数对象仅为当前 key 的有效交互格。
  - strict 越界: 若某四联通雷块平移后有任一雷格落在 key 外或非有效交互格, 则该平移向量不可被选择。
  - 组件之间的相对位置不保留; 只要求每个组件内部形状在平移后完整保留。

4) create_constraints 约束语义:
  - create_constraints 必须完整编码"存在对每个四联通雷块的独立平移方案, 使所有平移后的雷块两两不重叠, 且并集恰好为一个完整轴对齐矩形"。
  - 编码方式: 先按四连通把雷格拆成组件, 再枚举组件平移方案与候选矩形, 对每个候选建立可行性变量, 最后析取所有可行性变量(至少一个为真)。
  - 不允许只编码必要条件或只编码充分条件, 必须是必要且充分。

5) 可验证样例:
  - 样例A(应通过): 题板上有两个四联通雷块, 分别是两个 1x2 竖条; 其中一个块向右平移 1 格后, 两块并成 2x2 矩形。
  - 样例B(应失败): 只有一个 L 形四联通雷块, 无论如何平移都无法在不旋转的情况下与其他块一起拼成矩形。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ....abs.Lrule import AbstractMinesRule

if TYPE_CHECKING:
  from ....abs.board import AbstractBoard
  from ....impl.summon.solver import Switch


class RulePUZ(AbstractMinesRule):
  id = "PUZ"
  name = "Puzzle"
  name.zh_CN = "拼图"
  doc = "All 4-connected mine blocks can be rearranged by independent translation to form an axis-aligned rectangle"
  doc.zh_CN = "所有四联通雷块可通过独立平移重排成一个轴对齐矩形"
  author = ("NT", 2201963934)
  tags = ["Original", "Global", "Construction", "Strong", "Extensive trial"]

  def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
    super().__init__(board, data)

  def create_constraints(self, board: "AbstractBoard", switch: "Switch"):
    model = board.get_model()
    rule_switch = switch.get(model, self)

    for key in board.get_interactive_keys():
      positions = [
        pos
        for pos, _ in sorted(board(key=key), key=lambda item: (item[0].x, item[0].y))
        if board.get_variable(pos, special="raw") is not None
      ]
      if not positions:
        model.Add(False).OnlyEnforceIf(rule_switch)
        continue

      var_list = [board.get_variable(pos, special="raw") for pos in positions]
      n = len(positions)
      pos_index = {(pos.x, pos.y): idx for idx, pos in enumerate(positions)}
      min_x = min(pos.x for pos in positions)
      max_x = max(pos.x for pos in positions)
      min_y = min(pos.y for pos in positions)
      max_y = max(pos.y for pos in positions)

      rectangles: list[list[int]] = []
      for x_min in range(min_x, max_x + 1):
        for x_max in range(x_min, max_x + 1):
          for y_min in range(min_y, max_y + 1):
            for y_max in range(y_min, max_y + 1):
              rect: list[int] = []
              ok = True
              for x in range(x_min, x_max + 1):
                for y in range(y_min, y_max + 1):
                  idx = pos_index.get((x, y))
                  if idx is None:
                    ok = False
                    break
                  rect.append(idx)
                if not ok:
                  break
              if ok:
                rectangles.append(rect)

      if not rectangles:
        model.Add(False).OnlyEnforceIf(rule_switch)
        continue

      shift_specs = [
        (dx, dy)
        for dx in range(-(max_x - min_x), max_x - min_x + 1)
        for dy in range(-(max_y - min_y), max_y - min_y + 1)
      ]
      if not shift_specs:
        model.Add(False).OnlyEnforceIf(rule_switch)
        continue

      shift_selects = [
        [model.NewBoolVar(f"puz_shift_{key}_{j}_{s}") for s in range(len(shift_specs))]
        for j in range(n)
      ]
      for j in range(n):
        model.Add(sum(shift_selects[j]) == var_list[j]).OnlyEnforceIf(rule_switch)

      # 四连通相邻的雷格必须共享同一个平移向量，从而等价于“按组件统一平移”。
      neighbor_pairs = []
      pos_set = set(pos_index)
      for j, pos in enumerate(positions):
        right = (pos.x, pos.y + 1)
        down = (pos.x + 1, pos.y)
        if right in pos_index:
          neighbor_pairs.append((j, pos_index[right]))
        if down in pos_index:
          neighbor_pairs.append((j, pos_index[down]))

      occupancy = [model.NewBoolVar(f"puz_occ_{key}_{q}") for q in range(n)]
      target_hits = [[] for _ in range(n)]
      source_hits = [[] for _ in range(n)]

      for j, pos in enumerate(positions):
        for s_idx, (dx, dy) in enumerate(shift_specs):
          hit = shift_selects[j][s_idx]
          source_hits[j].append(hit)

          target_idx = pos_index.get((pos.x + dx, pos.y + dy))
          if target_idx is None:
            model.Add(hit == 0).OnlyEnforceIf(rule_switch)
          else:
            target_hits[target_idx].append(hit)

        model.Add(sum(source_hits[j]) == var_list[j]).OnlyEnforceIf(rule_switch)

      for left_idx, right_idx in neighbor_pairs:
        for s_idx in range(len(shift_specs)):
          model.Add(shift_selects[left_idx][s_idx] == shift_selects[right_idx][s_idx]).OnlyEnforceIf([
            var_list[left_idx],
            var_list[right_idx],
            rule_switch,
          ])

      for q in range(n):
        if target_hits[q]:
          model.Add(sum(target_hits[q]) <= 1).OnlyEnforceIf(rule_switch)
          model.Add(sum(target_hits[q]) == occupancy[q]).OnlyEnforceIf(rule_switch)
        else:
          model.Add(occupancy[q] == 0).OnlyEnforceIf(rule_switch)

      rect_selects = []
      for rect_idx, rect in enumerate(rectangles):
        rect_select = model.NewBoolVar(f"puz_rect_{key}_{rect_idx}")
        rect_selects.append(rect_select)
        rect_set = set(rect)
        for q in range(n):
          if q in rect_set:
            model.Add(occupancy[q] == 1).OnlyEnforceIf([rect_select, rule_switch])
          else:
            model.Add(occupancy[q] == 0).OnlyEnforceIf([rect_select, rule_switch])

      model.Add(sum(rect_selects) == 1).OnlyEnforceIf(rule_switch)
