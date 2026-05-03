#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/04/06
# @Author  : GitHub Copilot
# @FileName: XS.py
"""
[XS] 分段 (Segment Split)

拆分定义：
1. 规则对象与适用范围：这是一个左线规则，作用于雷布局；实现类继承 `AbstractMinesRule`，约束所有启用的互动题板。
   该规则使用副板直接记录"每一行的所有分段位置"（不只是新增）。
2. 核心术语：
    - "段"指同一行上连续的一段格子；同一段内所有格子的雷/非雷状态相同。
    - 副板每个格子 (row, col) 对应主板行 row 中格 col 与 col+1 之间的分界；副板值为 1 表示该分界存在。
   - 跨段边界表示状态切换点：边界两侧格子状态必须不同。
   - “继承”指从下往上看，上一行的分段结构在左右顺序上保持对下一行的细分关系；上一行必须至少保留下一行已有的所有分段边界。此处应该使用副板约束实现。
   - “每行都比下方一行多分一次段”指每往上一行，段数都比下方多 1；若段数已经达到“每段恰好一格”的上限，则后续各行保持不变，不再继续分段。此处应该使用副板约束实现。
3. 计数对象、边界条件、越界处理：
   - 计数对象是每一行的段数(也就是副板的雷数)，不是主板雷数。
   - 底下第一行必须分成 2 段。
   - 当某行的段数已经等于该行的格数时，说明每段已经恰好 1 格，后续行不再增加段数。
   - 副板尺寸定义为 `主板高度 x (主板宽度-1)`，每个副板格子 (row, col) 一一对应主板行 row 的第 col 个分界；副板值为 1 表示该分界被选中。
   - 底行副板有恰好 1 个 1（对应 2 段）；往上每行递增一个 1，直到列数上限为止。例如 5x5 主板（副板 5x4）：底行 1 个 1，第 2-4 行分别 2、3、4 个 1，第 5 行保持 4 个 1。
   - 唯一性约束：每行恰好 min(row_index+1, W-1) 个 1；每列最多 1 个 1（确保某个分界位置只在某一行被新增、不在多行同时出现）。
4. fill 阶段与 create_constraints 阶段：
   - fill 阶段应在副板上展示每一行可选新增分段位置，并与最终约束含义一致。
    - create_constraints 阶段必须表达与上述拆分定义等价的约束：
      (a) 无边界处两侧必须同值；(主副板关系)
      (b) 两侧不同时必须是边界；(主副板关系)
      (c) 从下到上每行都在继承下方分段结构的基础上增加一段，直到达到单格段上限后保持不变；新增分段位置由副板变量指示。(副板约束)
5. 可验证样例：
   - 5x5 棋盘，副板 5x4。自底向上段数为 2、3、4、5、5（对应副板 1、2、3、4、4 个 1）。每列最多 1 个 1，每行恰好 min(row_index+1, 4) 个 1。
"""

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class RuleXS(AbstractMinesRule):
   id = "XS"
   name = "Segment Split"
   name.zh_CN = "分段"
   doc = "Uses sub-board to represent row segment boundaries: no boundary means same value, different sides must be boundary, boundary count increases from bottom up with row inheritance"
   doc.zh_CN = "用副板表示行分段边界：无边界同值、两侧不同必为边界，边界数自底向上递增并满足行间继承"
   author = ("NT", 2201963934)

   @staticmethod
   def _sub_key(key: str) -> str:
      return f"XS_{key}"

   def _ensure_sub_board(self, board: "AbstractBoard", key: str) -> tuple[int, int, str]:
      size = board.get_config(key, "size")
      if not isinstance(size, tuple) or len(size) != 2:
         return 0, 0, self._sub_key(key)
      h = int(size[0])
      w = int(size[1])
      seg_w = max(w - 1, 0)
      sub_key = self._sub_key(key)
      board.generate_board(sub_key, size=(h, seg_w))
      return h, w, sub_key

   def init_clear(self, board: "AbstractBoard"):
      board_data = getattr(board, "board_data", {})
      for key in board.get_interactive_keys():
         sub_key = self._sub_key(key)
         if sub_key not in board_data:
            continue
         for pos, _ in board(key=sub_key):
            board.set_value(pos, None)

   def create_constraints(self, board: "AbstractBoard", switch):
      # 先创建所有互动副板，再初始化 model，避免缺失 variable 层
      board_infos = [
         (key, *self._ensure_sub_board(board, key))
         for key in board.get_interactive_keys()
      ]

      model = board.get_model()
      s = switch.get(model, self)

      # 兼容外部已提前初始化 model 的场景：为新建副板补齐 variable 层
      for _, h, w, sub_key in board_infos:
         seg_w = max(w - 1, 0)
         data = board.board_data.get(sub_key, {})
         variable = data.get("variable")
         need_build = (
            variable is None
            or len(variable) != h
            or (h > 0 and len(variable[0]) != seg_w)
         )
         if need_build:
            data["variable"] = [[None for _ in range(seg_w)] for _ in range(h)]
            for x in range(h):
               for y in range(seg_w):
                  data["variable"][x][y] = model.NewBoolVar(
                     f"var({board.get_pos(x, y, sub_key)})"
                  )

      for key, h, w, sub_key in board_infos:
         seg_w = max(w - 1, 0)

         # 每行边界数：按从下到上 r=0..H-1，对应 min(r+1, W-1)
         for x in range(h):
            row_vars = [
               board.get_variable(board.get_pos(x, y, sub_key))
               for y in range(seg_w)
            ]
            target = min(h - x, seg_w)
            if row_vars:
               model.Add(sum(row_vars) == target).OnlyEnforceIf(s)

         # 行间继承：上方行必须包含下方行已有边界（上 >= 下）
         for x in range(h - 1):
            for y in range(seg_w):
               b_up = board.get_variable(board.get_pos(x, y, sub_key))
               b_down = board.get_variable(board.get_pos(x + 1, y, sub_key))
               model.Add(b_up >= b_down).OnlyEnforceIf(s)

         # 说明：在上>=下的单调约束下，每列从上到下只能保持或从 1 变为 0，
         # 等价地从下到上“首次出现”的新增边界至多一次，无需再直接对 b 施加列 <= 1。

            # 主副板关系：无边界同值；两侧不同时必须是边界
         for x in range(h):
            for y in range(seg_w):
               b = board.get_variable(board.get_pos(x, y, sub_key))
               left_var = board.get_variable(board.get_pos(x, y, key))
               right_var = board.get_variable(board.get_pos(x, y + 1, key))
               model.Add(left_var == right_var).OnlyEnforceIf([s, b.Not()])
               model.Add(b == 1).OnlyEnforceIf([s, left_var, right_var.Not()])
               model.Add(b == 1).OnlyEnforceIf([s, left_var.Not(), right_var])
