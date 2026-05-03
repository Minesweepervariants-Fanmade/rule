"""
[FL] 周长：雷线索值表示所在雷区周长

规则拆分定义(验收基准):
1) 规则对象与适用范围:
    - 中线规则(Mrule)。
    - 约束对象是当前 interactive key 内所有有效格的 raw 状态。
    - 仅对雷格(raw=1)所属的四连通雷区赋值与建模；非雷格不产生该规则线索值。

2) 核心术语精确定义:
    - 雷区(mine region): 以四连通(上/下/左/右)定义的、由 raw=1 组成的极大连通块。
    - 所在雷区: 某个雷格所在的那个四连通极大连通块。
    - 周长(perimeter): 对某个雷区，统计该雷区内所有雷格四个方向上与“非雷格或棋盘外”相邻的单位边数量之和；每条单位边计 1。
      - 仅上下左右方向参与统计，斜对角不计。
      - 雷区内部相邻边不计入周长。
      - 棋盘边界外侧视为周长边。
    - 雷区周长的线索值: 同一个雷区内所有雷格共享同一个周长值。

3) 计数对象、边界条件、越界处理:
    - 仅统计 board(key=当前 key) 可枚举到、且 raw 变量非空的有效格。
    - 越界格、洞格、无效格不参与连通块构成，也不参与周长计数。
    - 单格雷区周长为 4。
    - 仅在四连通意义下判断是否属于同一雷区；对角相邻的雷格不视为同一区域。

4) fill 阶段与 create_constraints 阶段等价语义:
    - fill 语义: 先按四连通把所有雷格分解为若干极大雷区，再对每个雷区计算周长 P，向该雷区内每个雷格写入同一个雷线索值 P。
    - create_constraints 语义: 必须编码出与 fill 完全等价的布尔/整数组合约束，保证求解结果中每个雷区内所有雷格的线索值相同，且等于该雷区的四连通周长。
    - 等价要求: 不能只约束局部邻边或单个格的局部度数；必须覆盖整个连通块的总周长。

5) 可验证样例:
    - 样例A(应通过): 两个四连通相邻雷格组成 1x2 雷区，其周长应为 6，两个雷格的线索值都应为 6。
    - 样例B(应通过): 单个孤立雷格的周长应为 4，该雷格线索值应为 4。
    - 样例C(应失败): 若某个四连通雷区内存在两个雷格线索值不同，或线索值不等于其外边界单位边总数，则应判定违反规则。

实现约束:
- 规则逻辑实现由“规则实现代理”完成。
"""

from collections import deque

from ....abs.Mrule import AbstractMinesClueRule, AbstractMinesValue
from ....abs.board import AbstractBoard, AbstractPosition
from ...rule.Lrule.connect import connect


_KEY_CACHE: dict[tuple[int, str], dict[str, object]] = {}


class RuleFL(AbstractMinesClueRule):
    id = "FL"
    name = "Perimeter"
    name.zh_CN = "周长"
    doc = "Mines clue value represents the perimeter of its mine region"
    doc.zh_CN = "雷线索值表示所在雷区周长"
    tags = ["Original", "Local", "Construction"]

    @staticmethod
    def _neighbors4(pos: AbstractPosition) -> list[AbstractPosition]:
        return [pos.up(), pos.down(), pos.left(), pos.right()]

    @classmethod
    def _collect_region(
        cls,
        board: AbstractBoard,
        mine_set: set[AbstractPosition],
        start: AbstractPosition,
    ) -> set[AbstractPosition]:
        if start not in mine_set:
            return set()

        region = set()
        queue = deque([start])
        while queue:
            current = queue.popleft()
            if current in region:
                continue
            region.add(current)
            for neighbor in cls._neighbors4(current):
                if neighbor in region or neighbor not in mine_set:
                    continue
                if not board.in_bounds(neighbor):
                    continue
                queue.append(neighbor)
        return region

    @classmethod
    def _region_perimeter(
        cls,
        board: AbstractBoard,
        region: set[AbstractPosition],
    ) -> int:
        perimeter = 0
        region_set = set(region)
        for pos in region_set:
            for neighbor in cls._neighbors4(pos):
                if not board.in_bounds(neighbor):
                    perimeter += 1
                    continue
                neighbor_var = board.get_variable(neighbor, special="raw")
                if neighbor_var is None:
                    continue
                if neighbor not in region_set:
                    perimeter += 1
        return perimeter

    def fill(self, board: "AbstractBoard") -> "AbstractBoard":
        for key in board.get_interactive_keys():
            mines = [pos for pos, _ in board("F", key=key)]
            mine_set = set(mines)
            visited: set[AbstractPosition] = set()

            for start in mines:
                if start in visited:
                    continue
                region = self._collect_region(board, mine_set, start)
                visited.update(region)
                perimeter = self._region_perimeter(board, region)
                code = int(perimeter).to_bytes(2, "big")
                for pos in region:
                    board.set_value(pos, ValueFL(pos, code))
        return board

    def suggest_total(self, info: dict):
        ub = 0
        for key in info["interactive"]:
            ub += info["total"][key]
        info["soft_fn"](ub * 0.18, 0)

    @staticmethod
    def _build_key_cache(
        board: AbstractBoard,
        key: str,
        model,
        s,
    ) -> dict[str, object]:
        positions_vars = [
            (pos, var)
            for pos, var in board(key=key, mode="variable", special="raw")
            if var is not None
        ]
        positions = [pos for pos, _ in positions_vars]
        pos_index = {pos: idx for idx, pos in enumerate(positions)}

        component_ids = connect(
            model=model,
            board=board,
            switch=s,
            component_num=None,
            ub=False,
            connect_value=1,
            nei_value=1,
            positions_vars=positions_vars,
            special="raw",
        )

        return {
            "positions": positions,
            "pos_index": pos_index,
            "component_ids": component_ids,
            "raw_vars": [var for _, var in positions_vars],
        }

    def create_constraints(self, board: "AbstractBoard", switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            cache_key = (id(model), key)
            if cache_key not in _KEY_CACHE:
                _KEY_CACHE[cache_key] = self._build_key_cache(board, key, model, s)

            cache = _KEY_CACHE[cache_key]
            positions = cache["positions"]
            if not positions:
                continue

            component_ids = cache["component_ids"]
            pos_index = cache["pos_index"]
            raw_vars = cache["raw_vars"]

            for pos, obj in board("F", key=key):
                if not isinstance(obj, ValueFL):
                    continue
                raw_var = board.get_variable(pos, special="raw")
                if raw_var is not None:
                    model.Add(raw_var == 1).OnlyEnforceIf(s)

                idx = pos_index.get(pos)
                if idx is None:
                    continue

                anchor_component = component_ids[idx]
                same_vars = [None] * len(positions)
                for cell_idx, cell_raw in enumerate(raw_vars):
                    if cell_raw is None:
                        continue

                    same_var = model.NewBoolVar(f"[FL]same_{key}_{idx}_{cell_idx}")
                    same_vars[cell_idx] = same_var

                    same_component = model.NewBoolVar(f"[FL]same_component_{key}_{idx}_{cell_idx}")
                    model.Add(component_ids[cell_idx] == anchor_component).OnlyEnforceIf([same_component, s])
                    model.Add(component_ids[cell_idx] != anchor_component).OnlyEnforceIf([same_component.Not(), s])
                    model.Add(same_var <= same_component).OnlyEnforceIf(s)
                    model.Add(same_var <= cell_raw).OnlyEnforceIf(s)
                    model.Add(same_var >= same_component + cell_raw - 1).OnlyEnforceIf(s)

                edge_terms = []
                for cell_idx, cell_pos in enumerate(positions):
                    cell_same = same_vars[cell_idx]
                    if cell_same is None:
                        continue

                    for neighbor in self._neighbors4(cell_pos):
                        if not board.in_bounds(neighbor):
                            edge_terms.append(cell_same)
                            continue

                        neighbor_idx = pos_index.get(neighbor)
                        if neighbor_idx is None:
                            edge_terms.append(cell_same)
                            continue

                        neighbor_same = same_vars[neighbor_idx]
                        if neighbor_same is None:
                            edge_terms.append(cell_same)
                            continue

                        edge_bool = model.NewBoolVar(f"[FL]edge_{key}_{idx}_{cell_idx}_{neighbor_idx}")
                        model.Add(edge_bool <= cell_same).OnlyEnforceIf(s)
                        model.Add(edge_bool + neighbor_same <= 1).OnlyEnforceIf(s)
                        model.Add(edge_bool >= cell_same - neighbor_same).OnlyEnforceIf(s)
                        edge_terms.append(edge_bool)

                model.Add(sum(edge_terms) == obj.value).OnlyEnforceIf(s)


class ValueFL(AbstractMinesValue):
    def __init__(self, pos: AbstractPosition, code: bytes = None):
        self.pos = pos
        if code is None:
            self.value = 0
        elif len(code) == 1:
            self.value = code[0]
        else:
            self.value = int.from_bytes(code[:2], "big")

    def __repr__(self):
        return str(self.value)

    @classmethod
    def type(cls) -> bytes:
        return RuleFL.id.encode("ascii")

    def code(self) -> bytes:
        return int(self.value).to_bytes(2, "big")
