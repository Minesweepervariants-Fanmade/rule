#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[JB] 格调
作者: NT (2201963934)
最后编辑时间: 2026-04-08 15:57:01

规则拆分定义（验收基准）

1) 规则对象与适用范围
- 作用对象: 雷格（mine cells）的整体形状约束。
- 作用范围: 每个 interactive board key 内的全部雷格。
- 非雷格不直接参与计数，但可作为分隔使不同组互不接触。

2) 核心术语定义
- 四连通: 仅通过上/下/左/右相邻连接。
- 矩形雷区: 一个四连通分量，且其包围盒内所有格都为雷（轴对齐实心矩形）。
- 方形雷区: 宽 == 高 的矩形雷区。
- 非方形雷区: 宽 != 高 的矩形雷区。
- 短边: 非方形矩形的 min(宽, 高)。短边两角指该短边所在线段的两个端点。
- 对角接触: 两格只在角点相邻（八邻域相邻但非四邻域相邻）。
- 一组格调: 恰好由 3 个矩形雷区组成，其中:
  a) 恰有 1 个非方形矩形 + 2 个方形矩形；
  b) 该非方形矩形的某一条短边的两个角，分别与两个方形矩形发生一次对角接触；
  c) 3 个矩形之间不得有四邻接；
  d) 除 b) 指定的两次对角接触外，不允许额外接触（四邻接或其他对角接触）。
- 若干组且组间不相互接触: 全盘雷格可划分为若干个互不接触的组；不同组之间不存在任何接触（含四邻接与对角接触）。

3) 计数对象、边界条件、越界处理
- 本规则是结构约束，不产生数字计数线索；计数对象为“分量数量、矩形形状参数、接触关系数量”。
- 边界/角落允许出现合法矩形，越界邻居视为不存在（不构成接触）。
- 单组必须完整落在棋盘内；不得通过越界“补全”接触关系。

4) fill 与 create_constraints 语义等价
- fill 语义: 仅生成可被分解为若干合法“格调组”的雷图案。
- create_constraints 语义: 对任意候选雷图案施加必要且充分约束，使其当且仅当能分解为若干合法“格调组”。
- 两阶段在“组划分、矩形性、接触关系、组间隔离”四方面应严格一致。

5) 可验证样例（文字）
- 合法样例: 在 8x8 棋盘中放置一组由 1x3 非方形条形矩形 + 两个 1x1 方形矩形构成的图案。
  令非方形条形短边为竖向，短边两角分别在其上端与下端；在这两个角的对角位置各放置一个 1x1 雷块，且三者无四邻接，
  除这两处规定对角接触外无其他接触。该组合法。
- 非法样例A: 两个方形矩形有任意一个与非方形矩形发生四邻接。
- 非法样例B: 组内出现第 4 个矩形分量，或两个非方形分量。
- 非法样例C: 两组之间存在任意对角接触或四邻接。
"""

from __future__ import annotations

from itertools import combinations

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


def _interval_overlap_len(a1: int, a2: int, b1: int, b2: int) -> int:
  lo = max(a1, b1)
  hi = min(a2, b2)
  if hi < lo:
    return 0
  return hi - lo + 1


def _diag_touch_count(rect_a: dict, rect_b: dict) -> int:
  ax1, ay1, ax2, ay2 = rect_a["x1"], rect_a["y1"], rect_a["x2"], rect_a["y2"]
  bx1, by1, bx2, by2 = rect_b["x1"], rect_b["y1"], rect_b["x2"], rect_b["y2"]
  total = 0
  for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
    total += _interval_overlap_len(ax1, ax2, bx1 - dx, bx2 - dx) * _interval_overlap_len(
      ay1, ay2, by1 - dy, by2 - dy
    )
  return total


def _orth_touch(rect_a: dict, rect_b: dict) -> bool:
  ax1, ay1, ax2, ay2 = rect_a["x1"], rect_a["y1"], rect_a["x2"], rect_a["y2"]
  bx1, by1, bx2, by2 = rect_b["x1"], rect_b["y1"], rect_b["x2"], rect_b["y2"]
  overlap_x = _interval_overlap_len(ax1, ax2, bx1, bx2) > 0
  overlap_y = _interval_overlap_len(ay1, ay2, by1, by2) > 0
  share_vertical_edge = overlap_x and (ay2 + 1 == by1 or by2 + 1 == ay1)
  share_horizontal_edge = overlap_y and (ax2 + 1 == bx1 or bx2 + 1 == ax1)
  return share_vertical_edge or share_horizontal_edge


def _overlap(rect_a: dict, rect_b: dict) -> bool:
  return _interval_overlap_len(rect_a["x1"], rect_a["x2"], rect_b["x1"], rect_b["x2"]) > 0 and _interval_overlap_len(
    rect_a["y1"], rect_a["y2"], rect_b["y1"], rect_b["y2"]
  ) > 0


def _any_touch_or_overlap(rect_a: dict, rect_b: dict) -> bool:
  ax1, ay1, ax2, ay2 = rect_a["x1"], rect_a["y1"], rect_a["x2"], rect_a["y2"]
  bx1, by1, bx2, by2 = rect_b["x1"], rect_b["y1"], rect_b["x2"], rect_b["y2"]
  return not (ax2 + 1 < bx1 or bx2 + 1 < ax1 or ay2 + 1 < by1 or by2 + 1 < ay1)


def _corner_has_diag_contact(corner: tuple[int, int], rect_b: dict) -> bool:
  cx, cy = corner
  for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
    bx = cx + dx
    by = cy + dy
    if rect_b["x1"] <= bx <= rect_b["x2"] and rect_b["y1"] <= by <= rect_b["y2"]:
      return True
  return False


def _short_side_corners(rect: dict) -> list[tuple[tuple[int, int], tuple[int, int]]]:
  x1, y1, x2, y2 = rect["x1"], rect["y1"], rect["x2"], rect["y2"]
  h, w = rect["h"], rect["w"]
  if h < w:
    return [((x1, y1), (x2, y1)), ((x1, y2), (x2, y2))]
  if w < h:
    return [((x1, y1), (x1, y2)), ((x2, y1), (x2, y2))]
  return []


class RuleJB(AbstractMinesRule):
  name = ["JB", "格调"]
  doc = "雷格可分解为若干互不接触的格调组，每组由1个非方形矩形+2个方形矩形并按短边角对角接触组成"

  def create_constraints(self, board: "AbstractBoard", switch):
    model = board.get_model()
    s = switch.get(model, self)

    for key in board.get_interactive_keys():
      positions_vars = [(pos, var) for pos, var in board("always", mode="variable", key=key)]
      if not positions_vars:
        continue

      coord_to_var = {(pos.x, pos.y): var for pos, var in positions_vars}
      valid_coords = set(coord_to_var.keys())

      boundary = board.boundary(key)
      max_x = boundary.x
      max_y = boundary.y

      rectangles: list[dict] = []
      for x1 in range(max_x + 1):
        for y1 in range(max_y + 1):
          for x2 in range(x1, max_x + 1):
            for y2 in range(y1, max_y + 1):
              cells = [(x, y) for x in range(x1, x2 + 1) for y in range(y1, y2 + 1)]
              if any(cell not in valid_coords for cell in cells):
                continue
              h = x2 - x1 + 1
              w = y2 - y1 + 1
              rectangles.append(
                {
                  "id": len(rectangles),
                  "x1": x1,
                  "y1": y1,
                  "x2": x2,
                  "y2": y2,
                  "h": h,
                  "w": w,
                  "square": h == w,
                  "cells": tuple(cells),
                }
              )

      if not rectangles:
        continue

      pair_props: dict[tuple[int, int], dict] = {}
      for i, j in combinations(range(len(rectangles)), 2):
        a = rectangles[i]
        b = rectangles[j]
        overlap = _overlap(a, b)
        orth = _orth_touch(a, b)
        diag_cnt = _diag_touch_count(a, b)
        pair_props[(i, j)] = {
          "overlap": overlap,
          "orth": orth,
          "diag_cnt": diag_cnt,
          "any_touch": overlap or orth or diag_cnt > 0,
          "close": _any_touch_or_overlap(a, b),
        }

      squares = [r for r in rectangles if r["square"]]
      nonsquares = [r for r in rectangles if not r["square"]]

      groups: list[dict] = []
      for rn in nonsquares:
        short_sides = _short_side_corners(rn)
        if not short_sides:
          continue
        for corner_a, corner_b in short_sides:
          for rs1, rs2 in combinations(squares, 2):
            i_n = rn["id"]
            i_1 = rs1["id"]
            i_2 = rs2["id"]
            p_n1 = pair_props[(min(i_n, i_1), max(i_n, i_1))]
            p_n2 = pair_props[(min(i_n, i_2), max(i_n, i_2))]
            p_12 = pair_props[(min(i_1, i_2), max(i_1, i_2))]

            if p_n1["overlap"] or p_n2["overlap"] or p_12["any_touch"]:
              continue
            if p_n1["orth"] or p_n2["orth"]:
              continue
            if p_n1["diag_cnt"] != 1 or p_n2["diag_cnt"] != 1:
              continue

            n1_corner_a = _corner_has_diag_contact(corner_a, rs1)
            n1_corner_b = _corner_has_diag_contact(corner_b, rs1)
            n2_corner_a = _corner_has_diag_contact(corner_a, rs2)
            n2_corner_b = _corner_has_diag_contact(corner_b, rs2)

            # 非方形矩形短边两角必须分别对应不同方形矩形，且每对只发生一次对角接触。
            valid_direct = n1_corner_a and (not n1_corner_b) and (not n2_corner_a) and n2_corner_b
            valid_swap = n2_corner_a and (not n2_corner_b) and (not n1_corner_a) and n1_corner_b
            if not (valid_direct or valid_swap):
              continue

            group_cells = set(rn["cells"]) | set(rs1["cells"]) | set(rs2["cells"])
            groups.append(
              {
                "rect_ids": (i_n, i_1, i_2),
                "cells": tuple(group_cells),
              }
            )

      group_vars = []
      for idx, group in enumerate(groups):
        g_var = model.NewBoolVar(f"jb_group_{key}_{idx}")
        group_vars.append(g_var)
        for cell in group["cells"]:
          model.Add(coord_to_var[cell] == 1).OnlyEnforceIf([g_var, s])

      for i, j in combinations(range(len(groups)), 2):
        g1 = groups[i]
        g2 = groups[j]
        conflict = False
        for rid1 in g1["rect_ids"]:
          for rid2 in g2["rect_ids"]:
            if rid1 == rid2:
              conflict = True
              break
            pair = (min(rid1, rid2), max(rid1, rid2))
            if pair_props[pair]["close"]:
              conflict = True
              break
          if conflict:
            break
        if conflict:
          model.Add(group_vars[i] + group_vars[j] <= 1).OnlyEnforceIf(s)

      coord_to_group_vars: dict[tuple[int, int], list] = {coord: [] for coord in valid_coords}
      for g_var, group in zip(group_vars, groups):
        for cell in group["cells"]:
          coord_to_group_vars[cell].append(g_var)

      for coord, mine_var in coord_to_var.items():
        cover_vars = coord_to_group_vars[coord]
        if cover_vars:
          model.Add(sum(cover_vars) == mine_var).OnlyEnforceIf(s)
        else:
          model.Add(mine_var == 0).OnlyEnforceIf(s)
