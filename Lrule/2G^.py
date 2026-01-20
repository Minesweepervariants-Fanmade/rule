"""
[2G^] 互异连块：四连通雷区域面积为 1 到 N 各一个。(N = 题板尺寸 - 1)
"""
from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard, AbstractPosition, MASTER_BOARD
from ...rule.Lrule.connect import connect

from itertools import permutations

class Rule2G(AbstractMinesRule):
    name = ["2G^", "互异连块", "Group^"]
    doc = " 四连通雷区域的面积为 1 到 N 各一个。(N = 题板尺寸 - 1)"

    def create_constraints(self, board: AbstractBoard, switch):
        positions = [pos for pos, _ in board("always", mode="variable")]
        model = board.get_model()
        s = switch.get(model, self)
        size = board.get_config(MASTER_BOARD, "size")[0]
        n = len(positions)
        areas = size - 1
        root_vars = [model.NewBoolVar(f'root_{i}') for i in range(n)]

        component_ids = connect(
            model=model,
            board=board,
            switch=s,
            component_num=areas,
            ub=False,
            connect_value=1,
            nei_value=1,
            root_vars=root_vars,
            special='raw'
        )

        component_sizes = [model.NewIntVar(0, size * size, f'area_{i}') for i in range(len(positions))]
        for i, root_var in enumerate(root_vars):
            pos_in_component_vars = [model.NewBoolVar(f'pos_{j}_on_root_{i}') for j in positions]
            for j, pos_in_component_var in enumerate(pos_in_component_vars):
                mine_var = board.get_variable(positions[j], special='raw')
                model.Add(component_ids[j] == i).OnlyEnforceIf([mine_var, root_var, pos_in_component_var, s])
                model.Add(component_ids[j] != i).OnlyEnforceIf([mine_var, root_var, pos_in_component_var.Not(), s])
            model.Add(component_sizes[i] == sum(pos_in_component_vars)).OnlyEnforceIf(root_var, s)
            model.Add(component_sizes[i] == 0).OnlyEnforceIf(root_var.Not(), s)
        
        for root_var, component_size in zip(root_vars, component_sizes):
            model.Add(component_size >= 1).OnlyEnforceIf([root_var, s])
            model.Add(component_size <= areas).OnlyEnforceIf([root_var, s])

        for i in range(0, len(component_sizes) - 1):
            for j in range(i + 1, len(component_sizes)):  
                model.Add(component_sizes[i] != component_sizes[j]).OnlyEnforceIf([root_vars[i], root_vars[j], s])
        
    def suggest_total(self, info: dict):
        size = info["size"][MASTER_BOARD][0]
        expected_total = (size - 1) * size // 2  # 1 + 2 + ... + (N-1)
        def hard_constraint(m, total):
            m.Add(total == expected_total)
        info["hard_fns"].append(hard_constraint)

        