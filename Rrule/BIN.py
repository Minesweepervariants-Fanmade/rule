from typing import Dict, List
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition
from ..sharpRule.Csharp import FakeSwitch
from ....utils.tool import get_random
from ....impl.impl_obj import get_value
from ....utils.image_create import get_text, get_row
from ....utils.web_template import MultiNumber


class RuleBIN(AbstractClueRule):
    name = ["BIN", "二叉", "Binary"]
    doc = "BIN:X;Y 表示线索为 X 与 Y 规则下的值（顺序不确定）"

    def __init__(self, board: AbstractBoard = None, data: str = "") -> None:
        super().__init__(board, data)
        data_parts = data.split(";")
        if len(data_parts) != 2:
            raise ValueError("BIN rule requires two sub-rules")
        self.rule = (data_parts[0], data_parts[1])


    def fill(self, board: AbstractBoard) -> AbstractBoard:
        rules = [board.get_rule_instance(self.rule[0]), board.get_rule_instance(self.rule[1])]
        if not all(rules):
            raise ValueError("Sub-rules for BIN are not properly defined")
        boards: List[AbstractBoard] = []
        for rule in rules:
            boards.append(rule.fill(board.clone()))
        for key in board.get_board_keys():
            for pos, _ in board("N", key=key):
                values = [boards[i].get_value(pos) for i in range(2)]
                if get_random().randint(0, 1):
                    values[0], values[1] = values[1], values[0]
                value_tuple = (int(values[0].__repr__()), int(values[1].__repr__()))
                board.set_value(pos, ValueBIN(pos, value_tuple, self.rule, None))
        return board


class ValueBIN(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', value: tuple[int, int] = (0, 0), rule: tuple[str, str] = ("", ""), code: bytes | None = None):
        super().__init__(pos)
        if not code:
            self.value = value
            self.rule = rule
        else:
            self.value = (code[0], code[1])
            split_index = code.index(b',')
            self.rule = (code[2:split_index].decode("ascii"), code[split_index + 1:].decode("ascii"))

    def __repr__(self):
        return f"{self.value[0]} {self.value[1]}"
    
    @classmethod
    def type(cls) -> bytes:
        return "BIN".encode("ascii")
    
    def code(self) -> bytes:
        rule_bytes_1 = self.rule[0].encode("ascii")
        rule_bytes_2 = self.rule[1].encode("ascii")
        return bytes([self.value[0], self.value[1]]) + rule_bytes_1 + b',' + rule_bytes_2
    
    def high_light(self, board: AbstractBoard) -> List[AbstractPosition]:
        positions = set()
        for i in range(2):
            for j in range(2):
                clue = self.get_clue(self.value[i], self.rule[j])
                if clue:
                    hl = clue.high_light(board)
                    if hl:
                        positions.update(hl)
        return list(positions)
    
    def compose(self, board) -> Dict:
        disp = [self.value[0], self.value[1]]
        disp.sort()
        return get_row(
            get_text(str(disp[0])),
            get_text(str(disp[1]))
        )
    
    def web_component(self, board) -> Dict:
        return MultiNumber(sorted([self.value[0], self.value[1]]))
    
    def get_clue(self, value: int, rule: str) -> AbstractClueValue:
        clue_code = bytearray()
        clue_code.extend(rule.encode("ascii"))
        clue_code.extend(b'|')
        clue_code.extend(bytes([value]))
        return get_value(self.pos, bytes(clue_code))
    
    def create_constraints(self, board: AbstractBoard, switch):
        model = board.get_model()
        s = switch.get(model, self)

        clue1 = self.get_clue(self.value[0], self.rule[0])
        clue2 = self.get_clue(self.value[1], self.rule[1])
        clue3 = self.get_clue(self.value[0], self.rule[1])
        clue4 = self.get_clue(self.value[1], self.rule[0])

        select1 = model.NewBoolVar(f"BIN_select1_{self.pos}")
        select2 = model.NewBoolVar(f"BIN_select2_{self.pos}")
        model.Add(select1 == 0).OnlyEnforceIf(s.Not())
        model.Add(select2 == 0).OnlyEnforceIf(s.Not())
        model.Add(select1 + select2 == 1).OnlyEnforceIf(s)

        clue1.create_constraints(board, FakeSwitch(select1))
        clue2.create_constraints(board, FakeSwitch(select1))
        clue3.create_constraints(board, FakeSwitch(select2))
        clue4.create_constraints(board, FakeSwitch(select2))
        