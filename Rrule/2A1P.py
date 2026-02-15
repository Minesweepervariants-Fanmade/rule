"""
[2A1P] 面积 + 划分: 线索表示四方向相邻雷区域的数量。
"""
from typing import List, Dict, Set

from minesweepervariants.impl.summon.solver import Switch

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition
from ...rule.Lrule.connect import connect

class Rule2A1P(AbstractClueRule):
    name = ["2A1P", "面积 + 划分", "Area + Partition"]
    doc = "线索表示四方向相邻雷区域的数量"

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
            board.set_value(pos, Value2A1P(pos, len(areas_rev)))
                
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
        clues = [(pos, clue) for pos, clue in board("always", mode="object") if isinstance(clue, Value2A1P)]
        for clue in clues:
            pos, clue_obj = clue
            s = switch.get(model, clue_obj)
            unique_area_vars: List = []
            neis = [_pos for _pos in pos.neighbors(1) if board.in_bounds(_pos)]
            for i, nei in enumerate(neis):
                same_area_vars = [model.NewBoolVar(f"2A1P_same_area_{nei}_{j}") for j in range(i)]
                unique_var = model.NewBoolVar(f"2A1P_unique_area_{nei}")
                unique_area_vars.append(unique_var)
                nei_id = positions.index(nei)
                nei_var = board.get_variable(nei)
                for j in range(i):
                    model.Add(component_ids[nei_id] == component_ids[positions.index(neis[j])]).OnlyEnforceIf(same_area_vars[j], s)
                    model.Add(component_ids[nei_id] != component_ids[positions.index(neis[j])]).OnlyEnforceIf(same_area_vars[j].Not(), s)
                if same_area_vars:
                    model.Add(sum(same_area_vars) == 0).OnlyEnforceIf(unique_var, nei_var, s)
                    model.AddBoolOr(same_area_vars).OnlyEnforceIf(unique_var.Not(), nei_var, s)
                    model.Add(unique_var == 0).OnlyEnforceIf(nei_var.Not(), s)
                else:
                    model.Add(unique_var == nei_var).OnlyEnforceIf(s)
            model.Add(sum(unique_area_vars) == clue_obj.value).OnlyEnforceIf(s)
            
    
class Value2A1P(AbstractClueValue):
    def __init__(self, pos: AbstractPosition, value: int = 0, code: bytes = None) -> None:
        super().__init__(pos, code)
        if code is not None:
            self.value = code[0]
        else:
            self.value = value

    def __repr__(self):
        return str(self.value)

    @classmethod
    def type(cls) -> bytes:
        return Rule2A1P.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])
