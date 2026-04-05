"""
[CS] 罗盘：线索表示四方向各相邻雷区域中，在所示方向上比线索本身更远的单元格数量。
"""
from typing import List, Dict, Set

from minesweepervariants.impl.summon.solver import Switch

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition
from ...rule.Lrule.connect import connect

from ....utils.tool import get_logger, get_random
from ....utils.image_create import get_col, get_row, get_text

MISSING_VALUE = 250
UP = 0
RIGHT = 1
DOWN = 2
LEFT = 3

class RuleCS(AbstractClueRule):
    name = ["CS", "罗盘", "Compass"]
    doc = "线索表示四方向各相邻雷区域中，在所示方向上比线索本身更远的单元格数量。"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        def dfs(board: AbstractBoard, pos: AbstractPosition, from_pos: AbstractPosition | None, visited: Dict[AbstractPosition, int], check_mine: bool):
            if not board.in_bounds(pos):
                return
            if check_mine and board.get_type(pos) != "F":
                return
            if not check_mine and board.get_type(pos) == "F":
                return

            if from_pos is None:
                visited[pos] = len(visited)
                for nei in pos.neighbors(1):
                    dfs(board, nei, pos, visited, check_mine)
                return

            if not pos in visited:
                visited[pos] = visited[from_pos]
                for nei in pos.neighbors(1):
                    if from_pos != nei:
                        dfs(board, nei, pos, visited, check_mine)
            else:
                prev_id = visited[pos]
                curr_id = visited[from_pos]
                if prev_id != curr_id:
                    for p in visited:
                        if visited[p] == curr_id:
                            visited[p] = prev_id
        for pos, _ in board("N"):
            areas: Dict[AbstractPosition, int] = {}
            check_mine = True # 别改，约束目前只考虑雷区
            dfs(board, pos.left(), None, areas, check_mine)
            dfs(board, pos.up(), None, areas, check_mine)
            dfs(board, pos.right(), None, areas, check_mine)
            dfs(board, pos.down(), None, areas, check_mine)
            values = [0, 0, 0, 0]
            for p in areas:
                if p.x < pos.x:
                    values[UP] += 1
                elif p.x > pos.x:
                    values[DOWN] += 1
                if p.y < pos.y:
                    values[LEFT] += 1
                elif p.y > pos.y:
                    values[RIGHT] += 1
            for i in range(4):
                if get_random().randint(0, 1) == 0:
                    values[i] = MISSING_VALUE

            board.set_value(pos, ValueCS(pos, values))

        return board
    
class ValueCS(AbstractClueValue):
    def __init__(self, pos: AbstractPosition, values: list[int] = [MISSING_VALUE, MISSING_VALUE, MISSING_VALUE, MISSING_VALUE], code: bytes = None):
        super().__init__(pos, code)
        if code is not None:
            self.values: list[int] = list(code)
        else:
            self.values = values

    def __repr__(self):
        return ".".join([str(i) if i != MISSING_VALUE else "?" for i in self.values])
    
    def compose(self, board) -> Dict:
        return get_col(
            get_text(self.display_value(UP)),
            get_row(
                get_text(self.display_value(LEFT)),
                get_text(self.display_value(RIGHT)),
                spacing=0.125
            ),
            get_text(self.display_value(DOWN))
        )
    
    def display_value(self, index) -> str:
        return str(self.values[index]) if self.values[index] != MISSING_VALUE else "?"
        
    @classmethod
    def type(cls) -> bytes:
        return RuleCS.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes(self.values)
    
    def create_constraints(self, board: AbstractBoard, switch: Switch):
        model = board.get_model()
        s = switch.get(model, self)
        positions = [pos for pos, _ in board("always", mode="variable")]
        component_ids = connect(
            model=model,
            board=board,
            switch=s,
            component_num=None,
            ub=False,
            connect_value=1,
            nei_value=1,
            positions_vars=[(pos, var if pos != self.pos else model.NewConstant(1)) for pos, var in board("always", mode="variable")]
        )
        if (self.values[UP] != MISSING_VALUE):
            upper_poses = [(p, model.NewBoolVar("upper")) for p in positions if p.x < self.pos.x]
            for pos, var in upper_poses:
                model.Add(component_ids[positions.index(pos)] == component_ids[positions.index(self.pos)]).OnlyEnforceIf(s, var)
                model.Add(component_ids[positions.index(pos)] != component_ids[positions.index(self.pos)]).OnlyEnforceIf(s, var.Not())
            model.Add(self.values[UP] == sum(var for _, var in upper_poses)).OnlyEnforceIf(s)

        if (self.values[DOWN] != MISSING_VALUE):
            lower_poses = [(p, model.NewBoolVar("lower")) for p in positions if p.x > self.pos.x]
            for pos, var in lower_poses:
                model.Add(component_ids[positions.index(pos)] == component_ids[positions.index(self.pos)]).OnlyEnforceIf(s, var)
                model.Add(component_ids[positions.index(pos)] != component_ids[positions.index(self.pos)]).OnlyEnforceIf(s, var.Not())
            model.Add(self.values[DOWN] == sum(var for _, var in lower_poses)).OnlyEnforceIf(s)

        if (self.values[LEFT] != MISSING_VALUE):
            left_poses = [(p, model.NewBoolVar("left")) for p in positions if p.y < self.pos.y]
            for pos, var in left_poses:
                model.Add(component_ids[positions.index(pos)] == component_ids[positions.index(self.pos)]).OnlyEnforceIf(s, var)
                model.Add(component_ids[positions.index(pos)] != component_ids[positions.index(self.pos)]).OnlyEnforceIf(s, var.Not())
            model.Add(self.values[LEFT] == sum(var for _, var in left_poses)).OnlyEnforceIf(s)

        if (self.values[RIGHT] != MISSING_VALUE):
            right_poses = [(p, model.NewBoolVar("right")) for p in positions if p.y > self.pos.y]
            for pos, var in right_poses:
                model.Add(component_ids[positions.index(pos)] == component_ids[positions.index(self.pos)]).OnlyEnforceIf(s, var)
                model.Add(component_ids[positions.index(pos)] != component_ids[positions.index(self.pos)]).OnlyEnforceIf(s, var.Not())
            model.Add(self.values[RIGHT] == sum(var for _, var in right_poses)).OnlyEnforceIf(s)


