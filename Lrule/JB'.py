#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[JB'] JB'
作者: NT (2201963934)

=== 规则拆分定义 ===

## 1. 规则对象与适用范围
- 类型: Lrule (AbstractMinesRule)，雷布局规则，仅在 create_constraints 中建模，无 fill。
- 适用范围: 全局雷格（所有 interactive key 的雷区）。

## 2. 核心术语精确定义

### 2.1 格调（Pattern）
一个最小格调由 4 个格子组成，分布在 3×3 的包围盒内，分为两类格子：
- **金箔 (A)**: 2 个格子，位于包围盒的中间列（或旋转后的对应位置），呈竖直相邻排列。
- **魔丸 (B)**: 2 个格子，位于包围盒底部（或旋转后的对应位置）的两个角上，呈水平分离排列。

### 2.2 四方向旋转定义（以包围盒左上角为原点 (0,0)）

**旋转 0°（原始方向）**:
```
_ A _
_ A _
B _ B
```
- A 格: (0,1), (1,1)
- B 格: (2,0), (2,2)
- 包围盒: 3 行 × 3 列

**旋转 90°（顺时针）**:
```
B _ _
_ A A
B _ _
```
- A 格: (1,1), (1,2)
- B 格: (0,0), (2,0)
- 包围盒: 3 行 × 3 列

**旋转 180°**:
```
B _ B
_ A _
_ A _
```
- A 格: (1,1), (2,1)
- B 格: (0,0), (0,2)
- 包围盒: 3 行 × 3 列

**旋转 270°（逆时针）**:
```
_ _ B
A A _
_ _ B
```
- A 格: (1,0), (1,1)
- B 格: (0,2), (2,2)
- 包围盒: 3 行 × 3 列

## 3. 计数对象、边界条件、越界处理

### 3.1 计数对象
- 每个格调覆盖恰好 4 个格子（2A + 2B）。
- 所有雷格必须被至少一个活跃格调覆盖。
- 金箔 (A) 格：任意两个活跃格调不能共享同一个金箔格（即每个金箔格最多被一个格调以 A 角色覆盖）。
- 魔丸 (B) 格：允许多个活跃格调共享同一个魔丸格（即每个魔丸格可以被多个格调以 B 角色覆盖）。

### 3.2 边界条件
- 格调的包围盒（3×3）必须完全位于盘面边界内。
- 即对于边界为 (max_x, max_y) 的盘面，格调原点 (ox, oy) 满足 0 <= ox <= max_x-2, 0 <= oy <= max_y-2。

### 3.3 越界处理
- 包围盒超出边界的候选格调直接排除，不生成对应布尔变量。

## 4. fill 阶段语义与 create_constraints 阶段语义的等价关系
- 本规则为 Lrule，无 fill 阶段。
- create_constraints 中：
  a) 为每个合法位置×旋转方向生成一个布尔变量 `pattern_active[p]`。
  b) 若 `pattern_active[p] == 1`，则该格调的 4 个格子均为雷。
  c) 每个雷格至少被一个活跃格调覆盖。
  d) 每个金箔格最多被一个活跃格调以 A 角色覆盖。
  e) 魔丸格无共享限制。

## 5. 可验证样例

### 样例 1: 5×5 盘面，单个格调
- 在 5×5 盘面中放置一个旋转 0° 的格调，原点 (0,0)。
- 雷格: (0,1), (1,1), (2,0), (2,2) — 共 4 雷。
- 验证: 4 个雷格均被该格调覆盖，金箔格 (0,1) 和 (1,1) 仅被一个格调覆盖。

### 样例 2: 5×5 盘面，两个格调共享魔丸
- 格调 1: 旋转 0°, 原点 (0,0)，覆盖 (0,1)A, (1,1)A, (2,0)B, (2,2)B
- 格调 2: 旋转 180°, 原点 (2,0)，覆盖 (3,1)A, (4,1)A, (2,0)B, (2,2)B
- 共享魔丸: (2,0) 和 (2,2) 同时是格调 1 和格调 2 的 B 格。
- 验证: 魔丸共享合法，金箔无共享。

### 样例 3: 边界排除
- 5×5 盘面，格调原点 (3,0) 时包围盒 x 范围 [3,5]，超出 max_x=4，排除。
- 格调原点 (0,3) 时包围盒 y 范围 [3,5]，超出 max_y=4，排除。
"""

from dataclasses import dataclass
from typing import List, Tuple
from collections import defaultdict

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard, AbstractPosition

@dataclass(frozen=True)
class Pattern:
    rot: int
    a_rel: Tuple[Tuple[int, int], ...]
    b_rel: Tuple[Tuple[int, int], ...]

TEMPLATES: List[Pattern] = [
    Pattern(0, ((0,1),(1,1)), ((2,0),(2,2))),
    Pattern(1, ((1,1),(1,2)), ((0,0),(2,0))),
    Pattern(2, ((1,1),(2,1)), ((0,0),(0,2))),
    Pattern(3, ((1,0),(1,1)), ((0,2),(2,2))),
]

class RuleJBp(AbstractMinesRule):
    id = "JB'"
    name = "Some Dick"
    name.zh_CN = "几把"
    doc = "Some Dick: The minefield consists of several patterns of 4 cells (minimum) dick, which can intersect and share B cells, but cannot share A cells."
    doc.zh_CN = """几把：雷区由若干4格（最小）格调组成，可以交叉，可以共享魔丸，但不能共享金箔。"""
    author = ("NT", 2201963934)

    def create_constraints(self, board: AbstractBoard, switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            boundary = board.boundary(key=key)
            max_x = boundary.x
            max_y = boundary.y
            if max_x < 2 or max_y < 2:
                continue

            all_cover = defaultdict(list)
            a_cover = defaultdict(list)
            b_cover = defaultdict(list)
            pattern_info = []

            for ox in range(max_x - 1):
                for oy in range(max_y - 1):
                    for rot, pat in enumerate(TEMPLATES):
                        var = model.NewBoolVar(f"jbp_{key}_{ox}_{oy}_{rot}")
                        positions = []

                        # A
                        for dx, dy in pat.a_rel:
                            px = ox + dx
                            py = oy + dy
                            pos = board.get_pos(px, py, key=key)
                            all_cover[(px, py)].append(var)
                            a_cover[(px, py)].append(var)
                            positions.append(pos)

                        # B
                        for dx, dy in pat.b_rel:
                            px = ox + dx
                            py = oy + dy
                            pos = board.get_pos(px, py, key=key)
                            b_cover[(px, py)].append(var)
                            all_cover[(px, py)].append(var)
                            positions.append(pos)

                        pattern_info.append((var, positions))

            # active => mines
            for var, positions in pattern_info:
                for pos in positions:
                    mine_var = board.get_variable(pos)
                    model.AddImplication(var, mine_var).OnlyEnforceIf(s)

            # mine => covered
            for x in range(max_x + 1):
                for y in range(max_y + 1):
                    covers = all_cover[(x, y)]
                    if covers:
                        pos = board.get_pos(x, y, key=key)
                        mine_var = board.get_variable(pos)
                        model.Add(sum(covers) >= mine_var).OnlyEnforceIf(s)

            # A <=1
            for cell, vars_list in a_cover.items():
                model.Add(sum(vars_list) <= 1).OnlyEnforceIf(s)

            # A覆盖 => 无B覆盖（A格不能被其他格调以B角色占据）
            for cell in a_cover:
                a_vars = a_cover[cell]
                b_vars = b_cover.get(cell, [])
                if b_vars:
                    # sum(a_vars) >= 1 => sum(b_vars) == 0
                    # 用辅助变量: has_a => sum(b_vars) == 0
                    has_a = model.NewBoolVar(f"jbp_has_a_{cell[0]}_{cell[1]}_{key}")
                    model.Add(sum(a_vars) >= 1).OnlyEnforceIf(has_a)
                    model.Add(sum(a_vars) == 0).OnlyEnforceIf(has_a.Not())
                    model.Add(sum(b_vars) == 0).OnlyEnforceIf([has_a, s])