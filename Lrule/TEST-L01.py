"""
[TEST-L01]
"""
from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard
from .connect import connect


class RuleTESTL01(AbstractMinesRule):
    name = ["TEST-L01"]
    doc = "所有雷组成两个四连通块，左下角与右上角必为雷且不联通"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            boundary = board.boundary(key)

            # 构造固定顺序的 (pos, var) 列表，便于用 connect 返回的 component_ids 对应到具体格子
            positions_vars = [(pos, var) for pos, var in board("always", mode="variable")]
            if not positions_vars:
                continue

            # 计算四连通的分量，要求恰好 2 个
            component_ids = connect(
                model=model,
                board=board,
                switch=s,
                component_num=2,
                connect_value=1,  # 雷连通
                nei_value=1,      # 四连通
                positions_vars=positions_vars,
            )

            # 取左下角与右上角位置与变量
            bl_pos = board.get_pos(0, boundary.y, key)             # 左下角 (x=0, y=max)
            tr_pos = board.get_pos(boundary.x, 0, key)             # 右上角 (x=max, y=0)
            bl_var = board.get_variable(bl_pos)
            tr_var = board.get_variable(tr_pos)

            # 强制两角为雷
            if bl_var is not None:
                model.Add(bl_var == 1).OnlyEnforceIf(s)
            if tr_var is not None:
                model.Add(tr_var == 1).OnlyEnforceIf(s)

            # 强制两角不在同一连通块
            # 找到两角在 positions_vars 中的索引以读取对应 component_id
            bl_idx = next((i for i, (p, _) in enumerate(positions_vars) if p == bl_pos), None)
            tr_idx = next((i for i, (p, _) in enumerate(positions_vars) if p == tr_pos), None)
            if bl_idx is not None and tr_idx is not None:
                model.Add(component_ids[bl_idx] != component_ids[tr_idx]).OnlyEnforceIf(s)

    def suggest_total(self, info: dict):
        # 至少两角为雷，两个连通块最低各 1 格：建议总雷数 >= 2
        # 若棋盘较小，可建议每块最小为 2 以避免退化，但这里保持通用下限 2。
        total_min = 0
        for key in info["interactive"]:
            total_min += 2
        # 优先级 0：一般建议，不强制
        info["soft_fn"](total_min, 0)
