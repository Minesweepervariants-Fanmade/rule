"""
[TR] 树。
作者: NT (2201963934)

规则拆分定义(验收基准):
1) 规则对象与适用范围:
   - 左线规则(Lrule)。
   - 约束对象为同一 interactive key 内所有非雷格(raw != 1)形成的四联通无向图。
   - 该图必须是一棵树, 不是“包含一棵树”或“存在一棵树”即可, 而是整个非雷格图本身必须满足树定义。

2) 核心术语精确定义:
   - 非雷格: raw 状态不为雷的有效格。
   - 四联通边: 两个非雷格在上、下、左、右方向相邻时, 视为一条无向边。
   - 非雷格图: 所有非雷格作为节点, 四联通相邻关系作为边构成的无向图。
   - 树: 非雷格图必须连通且无环, 等价于节点数 n 与边数 m 满足 m = n - 1。

3) 计数对象、边界条件、越界处理:
   - 只统计当前 key 中的有效格; 越界格、无效格不参与节点或边计数。
   - 边只统计一次, 仅统计右邻与下邻即可避免重复计数。
   - 若非雷格节点数为 0 或 1, 视为树, 因为满足 m = n - 1。
   - 边界格/角格只按其有效四邻居参与计数, 与中心格规则一致。

4) fill 阶段与 create_constraints 阶段等价语义:
   - fill 语义: 若某盘面中的非雷格图满足“连通且边数 = 节点数 - 1”, 则该盘面满足规则; 否则不满足。
   - create_constraints 语义: 对同一 key 的非雷格集合, 编码出“全图连通”与“无环(边数 = 节点数 - 1)”的等价约束。
   - 等价要求: 不能只约束局部度数, 也不能只约束连通性; 两者缺一不可。

5) 可验证样例:
   - 样例A(应通过): 5x5 盘面中非雷格恰好形成一条四联通路径, 节点 5 个、边 4 条, 满足树。
   - 样例B(应失败): 5x5 盘面中存在一个 2x2 的非雷格环, 节点 4 个、边 4 条, 因 m != n - 1 且有环而失败。
   - 样例C(应通过): 只有 1 个非雷格节点时, 节点 1 个、边 0 条, 满足 m = n - 1。
"""

from ....abs.Lrule import AbstractMinesRule


class RuleTR(AbstractMinesRule):
    id = "TR"
    name = "Tree"
    name.zh_CN = "树"
    doc = "The orthogonally connected graph of non-mine cells is a tree."
    doc.zh_CN = "非雷格四联通形成的无向图是一棵树。"
    author = ("NT", 2201963934)
    tags = ["Creative", "Global", "Connectivity", "Construction"]
    creation_time = "2026-05-05"

    def create_constraints(self, board, switch):
      model = board.get_model()
      s = switch.get(model, self)

      for key in board.get_interactive_keys():
         raw_positions = [
            (pos, raw_var)
            for pos, raw_var in board(key=key, mode="variable", special="raw")
            if raw_var is not None
         ]
         if not raw_positions:
            continue

         pos_to_index = {pos: index for index, (pos, _) in enumerate(raw_positions)}

         safe_vars = []
         safe_by_pos = {}
         for pos, raw_var in raw_positions:
            safe_var = model.NewBoolVar(f"{self.id}_safe_{key}_{pos.x}_{pos.y}")
            model.Add(safe_var + raw_var == 1).OnlyEnforceIf(s)
            safe_vars.append(safe_var)
            safe_by_pos[pos] = safe_var

         has_any = model.NewBoolVar(f"{self.id}_has_any_{key}")
         model.Add(sum(safe_vars) >= 1).OnlyEnforceIf([has_any, s])
         model.Add(sum(safe_vars) == 0).OnlyEnforceIf([has_any.Not(), s])

         root_flags = []
         level_vars = []
         for pos, _ in raw_positions:
            root_flag = model.NewBoolVar(f"{self.id}_root_{key}_{pos.x}_{pos.y}")
            root_flags.append(root_flag)

            level_var = model.NewIntVar(0, len(raw_positions), f"{self.id}_level_{key}_{pos.x}_{pos.y}")
            level_vars.append(level_var)

            model.Add(root_flag <= safe_by_pos[pos]).OnlyEnforceIf(s)
            model.Add(level_var == 0).OnlyEnforceIf([safe_by_pos[pos].Not(), s])
            model.Add(level_var == 1).OnlyEnforceIf([root_flag, s])
            model.Add(level_var >= 2).OnlyEnforceIf([safe_by_pos[pos], root_flag.Not(), s])

         model.Add(sum(root_flags) == 1).OnlyEnforceIf([has_any, s])
         model.Add(sum(root_flags) == 0).OnlyEnforceIf([has_any.Not(), s])

         for index, (pos, _) in enumerate(raw_positions):
            choices = [root_flags[index]]

            for neighbor in (pos.up(), pos.down(), pos.left(), pos.right()):
               neighbor_index = pos_to_index.get(neighbor)
               if neighbor_index is None:
                  continue

               parent_choice = model.NewBoolVar(
                  f"{self.id}_parent_{key}_{neighbor.x}_{neighbor.y}_to_{pos.x}_{pos.y}"
               )
               model.AddImplication(parent_choice, safe_by_pos[neighbor]).OnlyEnforceIf(s)
               model.Add(level_vars[index] == level_vars[neighbor_index] + 1).OnlyEnforceIf([parent_choice, s])
               choices.append(parent_choice)

            model.Add(sum(choices) == 1).OnlyEnforceIf([safe_by_pos[pos], s])
            model.Add(sum(choices) == 0).OnlyEnforceIf([safe_by_pos[pos].Not(), s])

         edge_vars = []
         for pos, _ in raw_positions:
            current_safe = safe_by_pos[pos]
            for neighbor in (pos.right(), pos.down()):
               neighbor_safe = safe_by_pos.get(neighbor)
               if neighbor_safe is None:
                  continue

               edge_var = model.NewBoolVar(
                  f"{self.id}_edge_{key}_{pos.x}_{pos.y}_{neighbor.x}_{neighbor.y}"
               )
               model.Add(edge_var <= current_safe).OnlyEnforceIf(s)
               model.Add(edge_var <= neighbor_safe).OnlyEnforceIf(s)
               model.Add(edge_var >= current_safe + neighbor_safe - 1).OnlyEnforceIf(s)
               edge_vars.append(edge_var)

         model.Add(sum(edge_vars) == sum(safe_vars) - 1).OnlyEnforceIf([has_any, s])
         model.Add(sum(edge_vars) == 0).OnlyEnforceIf([has_any.Not(), s])