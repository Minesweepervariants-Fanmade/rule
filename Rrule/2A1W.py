"""
[2A1W] 面积 + 数墙: 线索表示四方向各相邻雷区域的面积。
"""
from typing import List, Dict, Set

from minesweepervariants.impl.summon.solver import Switch

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition
from ...rule.Lrule.connect import connect
from ....utils.image_create import get_text, get_row, get_col, get_dummy
from ....utils.web_template import MultiNumber

from itertools import permutations

class Rule2A1W(AbstractClueRule):
    name = ["2A1W", "面积 + 数墙", "Area + Wall"]
    doc = "线索表示四方向各相邻雷区域的面积"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        def dfs(board: AbstractBoard, pos: AbstractPosition, from_pos: AbstractPosition | None, visited: Dict[AbstractPosition, int]):
            if not board.in_bounds(pos):
                return
            
            if board.get_type(pos) != "F":
                return

            if from_pos is None:
                visited[pos] = len(visited)
                for nei in pos.neighbors(1):
                    dfs(board, nei, pos, visited)
                return

            if not pos in visited:
                visited[pos] = visited[from_pos]
                for nei in pos.neighbors(1):
                    if from_pos != nei:
                        dfs(board, nei, pos, visited)
            else:
                prev_id = visited[pos]
                curr_id = visited[from_pos]
                if prev_id != curr_id:
                    for p in visited:
                        if visited[p] == curr_id:
                            visited[p] = prev_id

        for pos, _ in board("N"):
            areas: Dict[AbstractPosition, int] = {}
            dfs(board, pos.left(), None, areas)
            dfs(board, pos.up(), None, areas)
            dfs(board, pos.right(), None, areas)
            dfs(board, pos.down(), None, areas)
            areas_rev: Dict[int, int] = {}
            for p in areas:
                id_ = areas[p]
                if id_ not in areas_rev:
                    areas_rev[id_] = 0
                areas_rev[id_] += 1
            board.set_value(pos, Value2A1W(pos, sorted(list(areas_rev.values()))))
                
        return board
    
    def create_constraints(self, board: AbstractBoard, switch: Switch):
        model = board.get_model()
        positions = [pos for pos, _ in board("always", mode="variable")]
        component_ids = connect(
            model=model,
            board=board,
            switch=model.NewConstant(1),
            component_num=None,
            ub=False,
            connect_value=1,
            nei_value=1,
        )
        clues = [(pos, clue) for pos, clue in board("always", mode="object") if isinstance(clue, Value2A1W)]
        for clue in clues:
            pos, clue_obj = clue
            s = switch.get(model, clue_obj)
            area_vars: List = []
            neis = [_pos for _pos in pos.neighbors(1) if board.in_bounds(_pos)]
            for i, nei in enumerate(neis):
                area_var = model.NewIntVar(0, len(positions), f"2A1W_area_{nei}")
                same_area_vars = [model.NewBoolVar(f"2A1W_same_area_{nei}_{j}") for j in range(i)]
                unique_var = model.NewBoolVar(f"2A1W_unique_area_{nei}")
                area_vars.append(area_var)
                nei_id = positions.index(nei)
                nei_var = board.get_variable(nei)
                for j in range(i):
                    model.Add(component_ids[nei_id] == component_ids[positions.index(neis[j])]).OnlyEnforceIf(same_area_vars[j], s)
                    model.Add(component_ids[nei_id] != component_ids[positions.index(neis[j])]).OnlyEnforceIf(same_area_vars[j].Not(), s)
                if same_area_vars:
                    model.Add(sum(same_area_vars) == 0).OnlyEnforceIf(unique_var, s)
                    model.AddBoolOr(same_area_vars).OnlyEnforceIf(unique_var.Not(), s)
                    model.Add(area_var == 0).OnlyEnforceIf(unique_var.Not(), s)
                else:
                    model.Add(unique_var == 1).OnlyEnforceIf(s)
                model.Add(area_var == 0).OnlyEnforceIf(nei_var.Not(), s)
                in_nei_area_vars = []
                for _pos in positions:
                    pos_in_nei_area = model.NewBoolVar(f"2A1W_pos_in_area_{_pos}_nei_{nei}")
                    in_nei_area_vars.append(pos_in_nei_area)
                    model.Add(component_ids[nei_id] == component_ids[positions.index(_pos)]).OnlyEnforceIf(pos_in_nei_area, nei_var, unique_var, s)
                    model.Add(component_ids[nei_id] != component_ids[positions.index(_pos)]).OnlyEnforceIf(pos_in_nei_area.Not(), nei_var, unique_var, s)
                model.Add(area_var == sum(in_nei_area_vars)).OnlyEnforceIf(nei_var, unique_var, s)

            possible_areas: List[List[int]] = []
            areas = list(clue_obj.values)
            if len(clue_obj.values) < len(neis):
                areas += [0] * (len(neis) - len(clue_obj.values))
            for perm in permutations(areas):
                possible_areas.append(list(perm))

            model.AddAllowedAssignments(area_vars, possible_areas).OnlyEnforceIf(s)
            
    
class Value2A1W(AbstractClueValue):
    def __init__(self, pos: AbstractPosition, values: list[int] = [], code: bytes = None) -> None:
        super().__init__(pos, code)
        if code is not None:
            self.values: list[int] = list(code)
        else:
            self.values = values

    def __repr__(self):
        return ".".join([str(i) for i in self.values]) if len(self.values) > 0 else "0"

    def web_component(self, board) -> Dict:
        if not self.values:
            return MultiNumber([0])
        return MultiNumber(self.values)

    def compose(self, board) -> Dict:
        if len(self.values) <= 1:
            value = 0
            if len(self.values) == 1:
                value = self.values[0]
            return get_col(
                get_dummy(height=0.175),
                get_text(str(value)),
                get_dummy(height=0.175),
            )
        if len(self.values) == 2:
            text_a = get_text(str(self.values[0]))
            text_b = get_text(str(self.values[1]))
            return get_col(
                get_dummy(height=0.175),
                get_row(
                    text_a,
                    text_b
                ),
                get_dummy(height=0.175),
            )
        elif len(self.values) == 3:
            text_a = get_text(str(self.values[0]))
            text_b = get_text(str(self.values[1]))
            text_c = get_text(str(self.values[2]))
            return get_col(
                get_row(
                    text_a,
                    text_b,
                    # spacing=0
                ),
                text_c,
            )
        elif len(self.values) == 4:
            text_a = get_text(str(self.values[0]))
            text_b = get_text(str(self.values[1]))
            text_c = get_text(str(self.values[2]))
            text_d = get_text(str(self.values[3]))
            return get_col(
                get_row(
                    text_a,
                    text_b,
                ),
                get_row(
                    text_c,
                    text_d
                )
            )
        else:
            # 我也不知道为什么会出现>5个数字的情况
            return get_text("")

    @classmethod
    def type(cls) -> bytes:
        return Rule2A1W.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes(self.values)

