"""
[3G]分组: 相同数字的雷线索四连通
"""

from typing import List, Dict

from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template

from ....abs.Mrule import AbstractMinesClueRule, AbstractMinesValue
from minesweepervariants.board import Board, Position
from ....utils.tool import get_random
from ...rule.Lrule.connect import connect
from ortools.sat.python.cp_model import IntVar

class Rule3G(AbstractMinesClueRule):
    id = "3G"
    name = "Grouping"
    name.zh_CN = "分组"
    doc = "Mines with the same number are 4-connected"
    doc.zh_CN = "相同数字的雷线索四连通"
    tags = ["Creative", "Local", "Construction"]
    creation_time = "2026-01-07"
    author = ("", 0)

    def fill(self, board: 'Board') -> 'Board':
        mines = [pos for pos, _ in board("F")]
        mine_set = set(mines)
        visited = set()
        components: List[List[Position]] = []

        for start in mines:
            if start in visited:
                continue

            stack = [start]
            component: List[Position] = []

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

    def create_constraints(self, board: Board, switch: Switch):
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


        for i, (pos1, clue1) in enumerate(clues):
            for pos2, clue2 in clues[i + 1:]:
                s1 = switch.get(model, clue1)
                s2 = switch.get(model, clue2)
                if clue1.value == clue2.value:
                    model.Add(component_ids[positions.index(pos1)] == component_ids[positions.index(pos2)]).OnlyEnforceIf([s1, s2])
                else:
                    model.Add(component_ids[positions.index(pos1)] != component_ids[positions.index(pos2)]).OnlyEnforceIf([s1, s2])


class MinesValue3G(AbstractMinesValue):
    id = Rule3G.id
    def __init__(self, pos: 'Position', code: bytes = None):
        self.pos = pos
        self.value = SingleIntValue(code[0], is_mine=True)

    @classmethod
    def from_json(cls, pos: 'Position', data: 'JSONObject') -> 'AbstractValue':
        _data = deep_unwrap(data)

        if not is_value_template(_data):
            raise TypeError()

        value = SingleIntValue.try_from(_data)

        if value is None:
            raise ValueError()

        return cls(pos, code=bytes([value.value]))
