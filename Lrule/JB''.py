#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[JB''] 貂蝉
作者: NT (2201963934)
最后编辑时间:2026-04-11 16:13:39

=== 规则拆分定义 ===

## 1. 规则对象与适用范围
- 类型: Lrule (AbstractMinesRule)，雷布局规则，仅在 create_constraints 中建模，无 fill。
- 适用范围: 全局雷区（所有 interactive key）。

## 2. 核心术语精确定义

### 2.1 蛇 (Snake)
- 参考1S.py定义：宽度为1的四连通路径，不存在分叉、环、交叉。
- 短边两端：路径的两端点（起点和终点）。
- 蛇自身可以接触：允许路径自触（相邻格触碰，但无环/交叉）。

### 2.2 正方形矩形 (Square Rectangle)
- 方形矩形：width == height >=1，所有格子为雷。

### 2.3 对角接触 (Diagonal Touch)
- 蛇的一头的两个端点中的一个（称为"连接端"）与两个正方形矩形的一角对角相邻；另一端（称为"自由端"）不与任何正方形对角接触。

### 2.4 接触限制
- 蛇的"连接端"与2个**不同**正方形矩形对角接触（该端连2个方）；"自由端"不接触任何正方形。
- 蛇与正方形/正方形间其他位置**完全不接触**：无重叠、无正交相邻、无其他对角相邻。
- 正方形间无接触限制（可触）。

## 3. 计数对象、边界条件、越界处理
- **全局构成**：雷区**恰好**由1条蛇 + 2个正方形矩形组成，**无多余雷**，**全覆盖**。
- 边界：路径/矩形格子在盘内。
- 越界：排除。

## 4. fill/create_constraints 等价
- Lrule，无fill。
- create_constraints：
  a) 枚举所有可能蛇路径（参考1S connect逻辑，但需端点标识）。
  b) 枚举所有方形矩形模板。
  c) 活跃var：sum(snake_var)==1, sum(square_var)==2。
  d) var=>覆盖格雷。
  e) 全雷覆盖>=1。
  f) 接触：连接端对角触方1+方2，自由端不触方。

## 5. 可验证样例
### 样例1: 最小蛇+小方
- 蛇：路径(0,0)-(0,1)-(0,2)，端(0,0)/(0,2)。
- 设端(0,0)为连接端，对角触方1@(1,0)和方2@(1,2)（各1个角）；端(0,2)为自由端，不触方。
- 验证：连接端触2方；自由端无触；蛇中格无触方；全雷=蛇3+方1+1=5。

### 样例2: 蛇自触
- 蛇U形自触中段，但连接端触2方，自由端无触，无其他触。

确认：蛇精确1S路径？端点对角触定义？方形大小>=1？正方间触允许？
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard, AbstractPosition

from .connect import connect

# =============================================================================
# 矩形模板工具 (复用自 JB.py 模式)
# =============================================================================

@dataclass(frozen=True)
class RectTemplate:
    """轴对齐矩形模板，含所有格子坐标。"""
    x1: int
    x2: int
    y1: int
    y2: int
    cells: Tuple[AbstractPosition, ...]
    square: bool

    @property
    def width(self) -> int:
        return self.y2 - self.y1 + 1

    @property
    def height(self) -> int:
        return self.x2 - self.x1 + 1


def _build_templates(board: AbstractBoard, key: str) -> List[RectTemplate]:
    """枚举所有轴对齐矩形模板（O(W²·H²)）。"""
    boundary = board.boundary(key=key)
    max_x = boundary.x
    max_y = boundary.y
    templates: List[RectTemplate] = []

    for x1 in range(max_x + 1):
        for x2 in range(x1, max_x + 1):
            for y1 in range(max_y + 1):
                for y2 in range(y1, max_y + 1):
                    cells = tuple(
                        board.get_pos(x, y, key)
                        for x in range(x1, x2 + 1)
                        for y in range(y1, y2 + 1)
                    )
                    templates.append(RectTemplate(
                        x1=x1, x2=x2, y1=y1, y2=y2,
                        cells=cells,
                        square=(x2 - x1) == (y2 - y1),
                    ))
    return templates


def _overlap(a: RectTemplate, b: RectTemplate) -> bool:
    """两个轴对齐矩形是否重叠。"""
    return not (
        a.x2 < b.x1 or b.x2 < a.x1 or
        a.y2 < b.y1 or b.y2 < a.y1
    )


# =============================================================================
# 常量
# =============================================================================

DIAG_DIRS = ((-1, -1), (-1, 1), (1, -1), (1, 1))
"""4 个对角方向位移。"""
ORTHO_DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))
"""4 个正交方向位移。"""


# =============================================================================
# RuleJBpp — 貂蝉
# =============================================================================

class RuleJBpp(AbstractMinesRule):
    id = "JB''"
    name = "entangledick"
    name.zh_CN = "貂蝉"
    doc = (
        "1 snake + 2 square rectangles = exact full cover. "
        "One snake endpoint diagonally touches two different square corners, "
        "the other endpoint touches none. "
        "No other contact (overlap/ortho/diag) between snake and squares. "
    )
    doc.zh_CN = (
        "雷区恰好由 1 蛇 + 2 正方形矩形完整覆盖。"
        "蛇的一个端点对角接触两个不同正方形矩形的一角，另一端点不接触任何正方形。"
        "蛇与正方形之间无其他接触（不重叠/不正交/不对角）。"
    )
    author = ("NT", 2201963934)

    # -------------------------------------------------------------------------
    #  主入口
    # -------------------------------------------------------------------------
    def create_constraints(self, board: AbstractBoard, switch):
        """
        对所有交互棋盘建立 JB'' 约束。

        阶段:
          A: 枚举所有正方形矩形模板
          B: 为每个模板创建激活布尔变量
          C: 构建格子→模板覆盖映射
          D: 创建每格分类变量（snake / in_square）
          E: 正方形约束（互斥 + 恰好 2 个）
          F: 蛇连通性 (connect)
          G: 蛇度数约束 + 端点检测
          H: 对角接触匹配
          I: 禁止非端点接触
        """
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            self._key_constraints(board, model, s, key)

    # -------------------------------------------------------------------------
    #  单 key 约束
    # -------------------------------------------------------------------------
    def _key_constraints(
        self,
        board: AbstractBoard,
        model,
        s,
        key: str,
    ):
        boundary = board.boundary(key=key)
        max_x = boundary.x
        max_y = boundary.y

        # ---- A: 枚举正方形矩形 ----
        all_templates = _build_templates(board, key)
        sq_templates = [t for t in all_templates if t.square]
        n_sq = len(sq_templates)
        if n_sq < 2:
            return  # 无法容纳 2 个不同正方形

        # ---- B: 激活变量 ----
        active_sq = [
            model.NewBoolVar(f"JBpp_sq_{key}_{i}")
            for i in range(n_sq)
        ]

        # ---- C: 格子→覆盖映射 ----
        cell_cover: Dict[Tuple[int, int], List[int]] = {}
        for idx, tpl in enumerate(sq_templates):
            for pos in tpl.cells:
                cell_cover.setdefault((pos.x, pos.y), []).append(idx)

        # ---- D: 每格分类变量 ----
        snake_var: Dict[Tuple[int, int], object] = {}
        in_sq_var: Dict[Tuple[int, int], object] = {}

        for x in range(max_x + 1):
            for y in range(max_y + 1):
                pos = board.get_pos(x, y, key)
                mine = board.get_variable(pos)

                # in_square: 是否被活跃正方形覆盖 (0 或 1, 因正方形不重叠)
                cover_indices = cell_cover.get((x, y), [])
                in_sq = model.NewBoolVar(f"JBpp_isq_{key}_{x}_{y}")
                model.Add(
                    in_sq == sum(active_sq[i] for i in cover_indices)
                ).OnlyEnforceIf(s)

                # snake: 是蛇的一部分 (mine = snake XOR square)
                sn = model.NewBoolVar(f"JBpp_sn_{key}_{x}_{y}")
                model.Add(sn + in_sq == mine).OnlyEnforceIf(s)

                snake_var[(x, y)] = sn
                in_sq_var[(x, y)] = in_sq

        # ---- E: 正方形约束 ----
        # E1: 重叠正方形互斥
        for i in range(n_sq):
            for j in range(i + 1, n_sq):
                if _overlap(sq_templates[i], sq_templates[j]):
                    model.Add(active_sq[i] + active_sq[j] <= 1).OnlyEnforceIf(s)
        # E2: 恰好 2 个活跃正方形
        model.Add(sum(active_sq) == 2).OnlyEnforceIf(s)

        # ---- F: 蛇连通性 ----
        snake_positions = [
            (board.get_pos(x, y, key), snake_var[(x, y)])
            for x in range(max_x + 1)
            for y in range(max_y + 1)
        ]

        connect(
            model=model,
            board=board,
            switch=s,
            connect_value=1,
            nei_value=1,       # 四连通
            component_num=1,   # 恰好 1 条蛇
            positions_vars=snake_positions,
        )

        # ---- G: 蛇度数约束 + 端点检测 ----
        endpoint_var: Dict[Tuple[int, int], object] = {}

        for x in range(max_x + 1):
            for y in range(max_y + 1):
                sn = snake_var[(x, y)]

                # 四连通蛇邻居
                neighbor_vars = []
                for dx, dy in ORTHO_DIRS:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx <= max_x and 0 <= ny <= max_y:
                        neighbor_vars.append(snake_var[(nx, ny)])

                # 宽度为 1: 每蛇格 1-2 个蛇邻居
                if neighbor_vars:
                    model.Add(
                        sum(neighbor_vars) >= 1
                    ).OnlyEnforceIf([sn, s])
                    model.Add(
                        sum(neighbor_vars) <= 2
                    ).OnlyEnforceIf([sn, s])

                # 端点: 恰好 1 个蛇邻居
                ep = model.NewBoolVar(f"JBpp_ep_{key}_{x}_{y}")
                if neighbor_vars:
                    model.Add(
                        sum(neighbor_vars) == 1
                    ).OnlyEnforceIf([ep, s])
                model.Add(sn == 1).OnlyEnforceIf([ep, s])
                endpoint_var[(x, y)] = ep

        # 恰好 2 个端点
        model.Add(sum(endpoint_var.values()) == 2).OnlyEnforceIf(s)

        # ---- H: 对角接触匹配 (情况1: 一头连2方, 另一头连0方) ----
        # H_pre: 预计算可达关系
        #   reachable_sq[(x,y)] = {模板索引 | 该模板有角点对角邻接 (x,y)}
        reachable_sq: Dict[Tuple[int, int], set] = {}
        for idx, tpl in enumerate(sq_templates):
            for cell in tpl.cells:
                cx, cy = cell.x, cell.y
                for dx, dy in DIAG_DIRS:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx <= max_x and 0 <= ny <= max_y:
                        reachable_sq.setdefault((nx, ny), set()).add(idx)

        # H1: 情况1约束 - 一头连2个方, 另一头连0个方
        # 每个端点可达的正方形数 * 端点变量，再求和 = 2
        ep_reachable_sum = []
        reach_var_map: Dict[Tuple[int, int], object] = {}
        for (x, y), sq_set in reachable_sq.items():
            ep = endpoint_var.get((x, y))
            if ep is None:
                continue
            if not sq_set:
                continue
            reach_var = model.NewIntVar(0, 2, f"JBpp_rch_{key}_{x}_{y}")
            count_expr = sum(active_sq[i] for i in sq_set)
            model.Add(reach_var == count_expr).OnlyEnforceIf([ep, s])
            model.Add(reach_var == 0).OnlyEnforceIf([ep.Not(), s])
            ep_reachable_sum.append(reach_var)
            reach_var_map[(x, y)] = reach_var
        model.Add(sum(ep_reachable_sum) == 2).OnlyEnforceIf(s)

        # H2: 禁止情况2 - 两端各触1方是禁止的
        # 统计有多少个端点的可达正方数 > 0（情况1: 1个端点，情况2: 2个端点）
        ep_has_touch_list = []
        for (x, y), sq_set in reachable_sq.items():
            ep = endpoint_var.get((x, y))
            if ep is None or not sq_set:
                continue
            reach_var = reach_var_map.get((x, y))
            if reach_var is None:
                continue
            has_touch = model.NewBoolVar(f"JBpp_ht_{key}_{x}_{y}")
            model.Add(reach_var >= 1).OnlyEnforceIf([has_touch, ep, s])
            model.Add(reach_var == 0).OnlyEnforceIf([has_touch.Not(), s])
            ep_has_touch_list.append(has_touch)
        model.Add(sum(ep_has_touch_list) == 1).OnlyEnforceIf(s)

        # ---- I: 禁止非端点接触 ----
        for x in range(max_x + 1):
            for y in range(max_y + 1):
                sn = snake_var[(x, y)]
                isq = in_sq_var[(x, y)]

                # I1: 正交接触 — 绝对禁止
                for dx, dy in ORTHO_DIRS:
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx <= max_x and 0 <= ny <= max_y):
                        continue
                    n_isq = in_sq_var.get((nx, ny))
                    if n_isq is None:
                        continue
                    # 仅检查 (x,y) 为蛇、(nx,ny) 为正方（反向由另半自动覆盖）
                    if x < nx or (x == nx and y < ny):
                        n_sn = snake_var[(nx, ny)]
                        model.Add(sn + n_isq <= 1).OnlyEnforceIf(s)
                        model.Add(isq + n_sn <= 1).OnlyEnforceIf(s)

                # I2: 对角接触 — 仅允许通过端点
                for dx, dy in DIAG_DIRS:
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx <= max_x and 0 <= ny <= max_y):
                        continue
                    n_isq = in_sq_var.get((nx, ny))
                    if n_isq is None:
                        continue
                    # 仅检查单向避免重复
                    if x < nx or (x == nx and y < ny):
                        n_sn = snake_var[(nx, ny)]
                        ep = endpoint_var.get((x, y))
                        ne_ep = endpoint_var.get((nx, ny))
                        if ep is not None:
                            model.Add(sn + n_isq <= 1 + ep).OnlyEnforceIf(s)
                        if ne_ep is not None:
                            model.Add(isq + n_sn <= 1 + ne_ep).OnlyEnforceIf(s)
