"""
[QTREE] 四叉树。

规则介绍:
- 将题版划分为四叉树，称所有节点均为雷的子树为大雷，
  大雷以外的节点不能有两个子节点同时为雷或大雷。

规则拆分定义(验收基准):
1) 规则对象与适用范围:
    - 左线规则(Lrule)。
    - 约束对象是当前 interactive key 内所有有效格的 raw 状态。
    - 题板形状前置条件: 当前 key 的有效格必须构成边长为 2^n 的正方形(例如 2x2, 4x4, 8x8)。
      不满足该条件时，规则判定为不可应用并报错(而非弱化或近似划分)。
    - 四叉树节点既包含叶子节点(单格)，也包含按递归划分得到的内部区域节点。
    - “是否为雷”用于叶子节点(raw=1)；“是否为大雷”用于任意节点(含叶与内部)。

2) 核心术语精确定义:
    - 四叉树划分: 仅当题板为 2^n x 2^n 正方形时成立，按几何中心对半分为四个等尺寸子正方形
      (左上/右上/左下/右下)，并递归执行直到 1x1 叶节点。
    - 节点: 四叉树中的一个区域(一组有效格)。
    - 子节点: 节点递归划分得到的四个直接后继区域中，含有效格者。
    - 大雷(heavy-mine subtree): 该节点覆盖的所有有效格均为雷(raw=1)。
      叶节点在该定义下与“该格为雷”等价。
    - 大雷以外的节点: 不满足“大雷”定义的节点。

3) 计数对象、边界条件、越界处理:
    - 仅统计 board(key=当前 key) 可枚举到的有效格；越界格、洞格、无效格不参与任何节点计数。
  - 对于合法形状(2^n 正方形)，每个内部节点恰有 4 个几何子节点。
    - 对于非正方形或边长非 2^n 的形状，不进入正常四叉树建模；在初始化阶段直接抛出 ValueError。
    - 对内部节点，只对“含有效格的子节点”计入子节点集合。
    - 若某节点有效子节点数小于 2，则“不能有两个子节点同时为雷或大雷”约束自然成立。

4) fill 阶段与 create_constraints 阶段等价语义:
    - fill 语义: 自顶向下检查每个非大雷节点，其子节点中“子节点为雷(单格)”或“子节点为大雷(区域)”
      的真值数量必须 <= 1。
    - create_constraints 语义: 对同一棵树、同一节点集合，编码出与 fill 完全等价的布尔约束，
      即对每个非大雷节点，满足 at-most-one(子节点为雷或大雷)。
    - 等价要求: 不可仅编码必要条件或仅部分层级；必须覆盖所有可达节点。

5) 可验证样例:
    - 样例A(应通过): 4x4 区域按四叉树划分后，某非大雷父节点四个子节点中至多 1 个为“雷或大雷”，其余为非雷混合，满足规则。
    - 样例B(应失败): 存在某非大雷父节点，其两个子节点分别为大雷(或一个叶雷 + 一个大雷)，应判定违反规则。
  - 样例C(应报错): 6x6 或 4x8 题板使用 QTREE 时，应因不满足 2^n 正方形前置条件而报错。
"""

from ....abs.Lrule import AbstractMinesRule


def _is_power_of_two(value: int) -> bool:
    return value > 0 and (value & (value - 1)) == 0


class RuleQTREE(AbstractMinesRule):
    id = "QTREE"
    name = "Quad Tree"
    name.zh_CN = "四叉树"
    doc = "将题版划分为四叉树，称所有节点均为雷的子树为大雷，大雷以外的节点不能有两个子节点同时为雷或大雷"

    def __init__(self, board=None, data=None):
        super().__init__(board, data)
        if board is None:
            return

        for key in board.get_interactive_keys():
            positions_vars = list(board(key=key, mode='variable', special='raw'))
            raw_map: dict[tuple[int, int], object] = {
                (pos.x, pos.y): raw_var
                for pos, raw_var in positions_vars
                if raw_var is not None
            }
            ok, reason, _, _ = self._validate_square(raw_map, key)
            if not ok:
                raise ValueError(
                    f"QTREE requires 2^n square board: key={key}, reason={reason}"
                )

    @staticmethod
    def _validate_square(
        raw_map: dict[tuple[int, int], object],
        key: str,
    ) -> tuple[bool, str, list[int], list[int]]:
        if not raw_map:
            return False, "has no valid raw cells", [], []

        xs = sorted({x for x, _ in raw_map.keys()})
        ys = sorted({y for _, y in raw_map.keys()})

        if len(xs) != len(ys):
            return False, f"width={len(xs)}, height={len(ys)}", xs, ys

        side = len(xs)
        if not _is_power_of_two(side):
            return False, f"side={side}", xs, ys

        if xs != list(range(xs[0], xs[0] + side)) or ys != list(range(ys[0], ys[0] + side)):
            return False, "coordinates are not contiguous", xs, ys

        for x in xs:
            for y in ys:
                if (x, y) not in raw_map:
                    return False, f"missing cell ({x}, {y})", xs, ys

        return True, "", xs, ys

    def create_constraints(self, board, switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            positions_vars = list(board(key=key, mode='variable', special='raw'))
            if not positions_vars:
                continue

            raw_map: dict[tuple[int, int], object] = {
                (pos.x, pos.y): raw_var
                for pos, raw_var in positions_vars
                if raw_var is not None
            }

            ok, reason, xs, ys = self._validate_square(raw_map, key)
            if not ok:
                raise ValueError(
                    f"QTREE requires 2^n square board: key={key}, reason={reason}"
                )

            side = len(xs)

            # 将坐标映射为紧凑索引，保证四叉树按几何中点严格对半。
            grid = [[raw_map[(x, y)] for y in ys] for x in xs]

            def build_node(x0: int, y0: int, size: int):
                heavy = model.NewBoolVar(f"qtree_heavy_{key}_{x0}_{y0}_{size}")

                if size == 1:
                    mine = grid[x0][y0]
                    model.Add(heavy == mine).OnlyEnforceIf(s)
                    return {
                        "heavy": heavy,
                        "is_leaf": True,
                        "mine": mine,
                    }

                half = size // 2
                children = [
                    build_node(x0, y0, half),
                    build_node(x0, y0 + half, half),
                    build_node(x0 + half, y0, half),
                    build_node(x0 + half, y0 + half, half),
                ]

                child_heavy_vars = [child["heavy"] for child in children]

                # 大雷定义：节点覆盖的所有有效格均为雷(通过子节点大雷递归等价编码)。
                model.Add(sum(child_heavy_vars) == 4).OnlyEnforceIf([s, heavy])
                model.Add(sum(child_heavy_vars) <= 3).OnlyEnforceIf([s, heavy.Not()])

                child_mine_or_heavy = [
                    child["mine"] if child["is_leaf"] else child["heavy"]
                    for child in children
                ]

                # 对每个非大雷内部节点: 四个子节点中“叶雷/子大雷”的数量 <= 1。
                model.Add(sum(child_mine_or_heavy) <= 1).OnlyEnforceIf([s, heavy.Not()])

                return {
                    "heavy": heavy,
                    "is_leaf": False,
                }

            build_node(0, 0, side)
