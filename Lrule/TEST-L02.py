"""
[TEST-L02] 雷总是组成L形，L形是宽度为1，拐弯一次的形状，L形可以斜角相邻但不能横竖相邻
"""

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class Rule4L(AbstractMinesRule):
    name = ["TEST-L02"]
    doc = "所有雷组成L形：雷总是组成L形，L形是宽度为1，拐弯一次的形状，L形可以斜角相邻但不能横竖相邻"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        # 收集棋盘位置与变量
        all_positions = []  # (x,y,pos,var)
        coords_to_pos = {}
        for pos, var in board(mode="variable"):
            if hasattr(pos, 'x') and hasattr(pos, 'y'):
                x, y = pos.x, pos.y
                all_positions.append((x, y, pos, var))
                coords_to_pos[(x, y)] = (pos, var)

        if not all_positions:
            return

        # 方向：0上、1右、2下、3左
        directions = [(0, -1), (1, 0), (0, 1), (-1, 0)]

        # 每格的分类变量：拐点 or 臂方向（四选一）
        corner_vars = {}  # (x,y) -> BoolVar
        arm_dir_vars = {}  # (x,y,dir_idx) -> BoolVar
        # 拐点的四种枚举方向（上+右、右+下、下+左、左+上）
        corner_orient_vars = {}  # (x,y,orient_idx 0..3) -> BoolVar

        for x, y, pos, var in all_positions:
            corner_vars[(x, y)] = model.NewBoolVar(f"corner_{x}_{y}")
            for d in range(4):
                arm_dir_vars[(x, y, d)] = model.NewBoolVar(f"arm_{x}_{y}_{d}")
            for o in range(4):
                corner_orient_vars[(x, y, o)] = model.NewBoolVar(f"corner_orient_{x}_{y}_{o}")

        # 分类一致性：var == corner + sum(arm_dir)
        for x, y, pos, var in all_positions:
            arm_sum = sum(arm_dir_vars[(x, y, d)] for d in range(4))
            model.Add(corner_vars[(x, y)] + arm_sum == var).OnlyEnforceIf(s)

        # 拐点枚举的方向对：(上,右)=0, (右,下)=1, (下,左)=2, (左,上)=3
        orient_pairs = [(0, 1), (1, 2), (2, 3), (3, 0)]

        # 约束A：拐点的四种枚举情况（选择一种），并且两邻居为臂且方向指向拐点，其余两邻居为空
        for x, y, pos, var in all_positions:
            is_corner = corner_vars[(x, y)]
            orient_sum = sum(corner_orient_vars[(x, y, o)] for o in range(4))
            # 拐点则必须选择一种方向；非拐点则不得选择
            model.Add(orient_sum == is_corner).OnlyEnforceIf(s)

            for o, (d1, d2) in enumerate(orient_pairs):
                co = corner_orient_vars[(x, y, o)]
                dx1, dy1 = directions[d1]
                dx2, dy2 = directions[d2]
                nx1, ny1 = x + dx1, y + dy1
                nx2, ny2 = x + dx2, y + dy2

                # 如果邻居不存在，则该拐点方向不可选
                if (nx1, ny1) not in coords_to_pos or (nx2, ny2) not in coords_to_pos:
                    model.Add(co == 0).OnlyEnforceIf(s)
                    continue

                _, n1_var = coords_to_pos[(nx1, ny1)]
                _, n2_var = coords_to_pos[(nx2, ny2)]

                # 其他两个方向（与d1,d2相对的两个）必须为空
                other_dirs = set([0, 1, 2, 3]) - set([d1, d2])
                for od in other_dirs:
                    odx, ody = directions[od]
                    nxo, nyo = x + odx, y + ody
                    if (nxo, nyo) in coords_to_pos:
                        _, novar = coords_to_pos[(nxo, nyo)]
                        model.Add(novar == 0).OnlyEnforceIf([co, s])

                # d1方向的邻居必须是臂，且其源方向指向当前拐点（邻居的源为相反方向）
                opp_d1 = (d1 + 2) % 4
                # d2方向的邻居亦同理
                opp_d2 = (d2 + 2) % 4

                # 邻居必须为雷
                model.Add(n1_var == 1).OnlyEnforceIf([co, s])
                model.Add(n2_var == 1).OnlyEnforceIf([co, s])

                # 邻居类型为臂（而非拐点）且方向指向拐点
                n1_arm = arm_dir_vars[(nx1, ny1, opp_d1)] if (nx1, ny1, opp_d1) in arm_dir_vars else None
                n2_arm = arm_dir_vars[(nx2, ny2, opp_d2)] if (nx2, ny2, opp_d2) in arm_dir_vars else None
                if n1_arm is not None:
                    model.Add(n1_arm == 1).OnlyEnforceIf([co, s])
                if n2_arm is not None:
                    model.Add(n2_arm == 1).OnlyEnforceIf([co, s])

        # 约束B：臂的源与垂直为空
        for x, y, pos, var in all_positions:
            for d in range(4):
                arm_d = arm_dir_vars[(x, y, d)]
                dx, dy = directions[d]
                nx, ny = x + dx, y + dy  # 源方向邻居

                # 如果该方向被选为臂的源方向
                # 1) 源邻居必须存在且为雷
                if (nx, ny) not in coords_to_pos:
                    # 邻居不存在则该方向不可选为臂源
                    model.Add(arm_d == 0).OnlyEnforceIf(s)
                else:
                    _, nvar = coords_to_pos[(nx, ny)]
                    model.Add(nvar == 1).OnlyEnforceIf([arm_d, s])

                    # 源邻居必须是拐点或同方向的臂（链向拐点）
                    n_corner = corner_vars[(nx, ny)] if (nx, ny) in corner_vars else None
                    n_arm_same = arm_dir_vars[(nx, ny, d)] if (nx, ny, d) in arm_dir_vars else None
                    if n_corner is not None and n_arm_same is not None:
                        model.Add(n_corner + n_arm_same >= 1).OnlyEnforceIf([arm_d, s])

                # 2) 与臂方向垂直的两个邻居必须为空
                perp = []
                if d in (0, 2):  # 上/下 -> 垂直为左/右
                    perp = [3, 1]
                else:           # 左/右 -> 垂直为上/下
                    perp = [0, 2]
                for pd in perp:
                    pdx, pdy = directions[pd]
                    px, py = x + pdx, y + pdy
                    if (px, py) in coords_to_pos:
                        _, pvar = coords_to_pos[(px, py)]
                        model.Add(pvar == 0).OnlyEnforceIf([arm_d, s])

        # 约束D：臂的反向邻居若为雷，则必须是同方向的臂（沿轴成直链）
        for x, y, pos, var in all_positions:
            for d in range(4):
                arm_d = arm_dir_vars[(x, y, d)]
                dx, dy = directions[d]
                bx, by = x - dx, y - dy  # 臂方向的反向格子
                if (bx, by) in coords_to_pos:
                    _, bvar = coords_to_pos[(bx, by)]
                    # 若当前为该方向的臂且反向邻居是雷，则反向邻居必须是同方向的臂
                    if (bx, by, d) in arm_dir_vars:
                        b_arm_same_dir = arm_dir_vars[(bx, by, d)]
                        model.Add(b_arm_same_dir == 1).OnlyEnforceIf([arm_d, bvar, s])

        # 约束C：拐点数量不超过20（可为0）
        total_corners = sum(corner_vars[(x, y)] for x, y, _, _ in all_positions)
        model.Add(total_corners <= 20).OnlyEnforceIf(s)

    def suggest_total(self, info: dict):
        target = 0
        for key in info["interactive"]:
            w, h = info["size"][key]
            total = info["total"][key]
            # L形由两个臂延伸，密度不宜过大；建议 ~35% 密度或接近用户意图
            max_mines = w * h
            suggested = min(int(max_mines * 0.35), max(3, total))
            target += suggested

        if target > 0:
            info["soft_fn"](target, 2)
