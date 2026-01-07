"""
[3G]分组: 相同数字的雷线索四连通
"""

from typing import List, Dict

from minesweepervariants.impl.summon.solver import Switch

from ....abs.Mrule import AbstractMinesClueRule, AbstractMinesValue
from ....abs.board import AbstractBoard, AbstractPosition
from ....utils.tool import get_random
from ...rule.Lrule.connect import connect
from ortools.sat.python.cp_model import IntVar

class Rule3G(AbstractMinesClueRule):
    name = ["3G", "分组", "Grouping"]
    doc = "相同数字的雷线索四连通"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        mines = [pos for pos, _ in board("F")]
        mine_set = set(mines)
        visited = set()
        components: List[List[AbstractPosition]] = []

        for start in mines:
            if start in visited:
                continue

            stack = [start]
            component: List[AbstractPosition] = []

            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                component.append(current)

                for neighbor in current.neighbors(1):
                    if neighbor in visited:
                        continue
                    if neighbor not in mine_set:
                        continue
                    stack.append(neighbor)

            components.append(component)

        get_random().shuffle(components)

        for group_id, component in enumerate(components):
            code = bytes([group_id])
            for cell in component:
                board.set_value(cell, MinesValue3G(cell, code))

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
        clues = [(pos, clue) for pos, clue in board("always", mode="object") if isinstance(clue, MinesValue3G)]

        for pos1, clue1 in clues:
            for pos2, clue2 in clues:
                if (clue1 == clue2):
                    continue
                s1 = switch.get(model, clue1)
                s2 = switch.get(model, clue2)
                if clue1.value == clue2.value:
                    model.Add(component_ids[positions.index(pos1)] == component_ids[positions.index(pos2)]).OnlyEnforceIf([s1, s2])
                else:
                    model.Add(component_ids[positions.index(pos1)] != component_ids[positions.index(pos2)]).OnlyEnforceIf([s1, s2])
        

class MinesValue3G(AbstractMinesValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = None):
        self.value = code[0]
        self.pos = pos

    def __repr__(self):
        return str(self.value)

    @classmethod
    def type(cls) -> bytes:
        return Rule3G.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])