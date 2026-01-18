from typing import List, Dict, Set

from minesweepervariants.impl.summon.solver import Switch

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition
from ...rule.Lrule.connect import connect
from ....utils.image_create import get_text, get_row, get_col, get_dummy
from ....utils.web_template import MultiNumber

from itertools import permutations

class Rule2A1Wl(AbstractClueRule):
    name = ["2A1W'", "面积 + 最大数墙", "Area + Largest Wall"]
    doc = "线索表示四方向最大相邻雷区域的面积"

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
            if areas_rev:
                board.set_value(pos, Value2A1Wl(pos, max(list(areas_rev.values()))))
            else:
                board.set_value(pos, Value2A1Wl(pos, 0))
                
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
        clues = [(pos, clue) for pos, clue in board("always", mode="object") if isinstance(clue, Value2A1Wl)]
        for clue in clues:
            pos, clue_obj = clue
            s = switch.get(model, clue_obj)
            area_vars = []
            neis = [_pos for _pos in pos.neighbors(1) if board.in_bounds(_pos)]
            for nei in neis:
                area_var = model.NewIntVar(0, len(positions), f"2A1W_area_{nei}")
                area_vars.append(area_var)
                nei_id = positions.index(nei)
                nei_var = board.get_variable(nei)
                model.Add(area_var == 0).OnlyEnforceIf(nei_var.Not(), s)
                in_nei_area_vars = []
                for _pos in positions:
                    pos_in_nei_area = model.NewBoolVar(f"2A1W_pos_in_area_{_pos}_nei_{nei}")
                    in_nei_area_vars.append(pos_in_nei_area)
                    model.Add(component_ids[nei_id] == component_ids[positions.index(_pos)]).OnlyEnforceIf(pos_in_nei_area, nei_var, s)
                    model.Add(component_ids[nei_id] != component_ids[positions.index(_pos)]).OnlyEnforceIf(pos_in_nei_area.Not(), nei_var, s)
                model.Add(area_var == sum(in_nei_area_vars)).OnlyEnforceIf(nei_var, s)

            # 我不知道为啥加了 OnlyEnforceIf(s) 模型会炸，反正没 switch 就没有对 area_vars 的约束，任意取值也肯定能过这个约束
            model.AddMaxEquality(clue_obj.value, area_vars)
            
    
class Value2A1Wl(AbstractClueValue):
    def __init__(self, pos: AbstractPosition, value: int = 0, code: bytes = None) -> None:
        super().__init__(pos, code)
        if code is not None:
            self.value = code[0]
        else:
            self.value = value

    def __repr__(self) -> str:
        return str(self.value)

    @classmethod
    def type(cls) -> bytes:
        return Rule2A1Wl.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])
