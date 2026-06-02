from typing import Dict, List, Optional
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition
from ..sharpRule.Csharp import FakeSwitch
from ....utils.impl_obj import VALUE_QUESS
from ....utils.tool import get_random
from ....impl.impl_obj import get_value
from ....utils.image_create import get_text, get_row
from ....utils.web_template import MultiNumber
from ....abs.board import ImmutableDict
from base64 import b64encode

VALUE_SPLIT: bytes = b'BIN_SPLIT_FLAG'


class RuleBIN(AbstractClueRule):
    id = "BIN"
    name = "Binary"
    name.zh_CN = "二叉"
    doc = "BIN:X;Y Clue indicates values under two rules X and Y (order not fixed)"
    doc.zh_CN = "BIN:X;Y 表示线索为 X 与 Y 规则下的值（顺序不确定）"
    tags = ["Variant", "Local", "Number Clue", "Extensive Trial"]
    creation_time = "2026-01-02"
    author = ("", 0)

    def __init__(self, board: AbstractBoard = None, data: str = "") -> None:
        super().__init__(board, data)
        data_parts = data.split(";")
        if len(data_parts) != 2:
            raise ValueError("BIN rule requires two sub-rules")

        self.rules = [
            board.get_rule_instance(
                rule_name=self._parse_rule_data(data_parts[0])[0],
                data=self._parse_rule_data(data_parts[0])[1], add=False
            ), board.get_rule_instance(
                rule_name=self._parse_rule_data(data_parts[1])[0],
                data=self._parse_rule_data(data_parts[1])[1], add=False
            )
        ]

    def _parse_rule_data(self, rule: str):
        # 解析规则 ID 和 data
        from minesweepervariants.impl.summon.summon import CONFIG
        parts = rule.split(CONFIG["delimiter"], 1)
        rule_id = parts[0]
        data = parts[1] if len(parts) == 2 else None
        return rule_id, data

    def fill(self, board: AbstractBoard) -> AbstractBoard:
        if not all(self.rules):
            raise ValueError("Sub-rules for BIN are not properly defined")
        boards: List[AbstractBoard] = []
        for rule in self.rules:
            boards.append(rule.fill(board.clone()))
        for key in board.get_interactive_keys():
            for pos, _ in board("N", key=key):
                values = [boards[i].get_value(pos) for i in range(2)]
                # if get_random().randint(0, 1):
                #     values[0], values[1] = values[1], values[0]
                rule_list: tuple[bytes, bytes] = (
                    values[0].type(),
                    values[1].type()
                )
                code_list: tuple[bytes, bytes] = (
                    values[0].code(),
                    values[1].code()
                )
                board.set_value(pos, ValueBIN(pos, code_list, rule_list, None))
        return board


class ValueBIN(AbstractClueValue):
    def __init__(
        self, pos: 'AbstractPosition',
        value: Optional[tuple[bytes, bytes]] = None,
        rule: Optional[tuple[bytes, bytes]] = None,
        code: bytes | None = None
    ):
        super().__init__(pos, b'')
        if not code:
            self.value: tuple[bytes, bytes] = value
            self.rule: tuple[bytes, bytes] = rule
        else:
            code_a, code_b, type_a, type_b = code.split(VALUE_SPLIT)
            self.value: tuple[bytes, bytes] = (code_a, code_b)
            self.rule: tuple[bytes, bytes] = (type_a, type_b)

    def __repr__(self):
        obj1 = self.get_clue(self.value[0], self.rule[0])
        obj2 = self.get_clue(self.value[1], self.rule[1])
        return " ".join(sorted([str(obj) for obj in [obj1, obj2]]))

    @classmethod
    def type(cls) -> bytes:
        return "BIN".encode("ascii")

    def code(self) -> bytes:
        code_a = self.value[0]
        code_b = self.value[1]
        type_a = self.rule[0]
        type_b = self.rule[1]
        return VALUE_SPLIT.join([code_a, code_b, type_a, type_b])

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
        obj1 = self.get_clue(self.value[0], self.rule[0])
        obj2 = self.get_clue(self.value[1], self.rule[1])
        return get_row(
            obj1.compose(board),
            obj2.compose(board)
        )

    def web_component(self, board) -> Dict:
        return MultiNumber(sorted([
            str(self.get_clue(self.value[0], self.rule[0])),
            str(self.get_clue(self.value[1], self.rule[1]))
        ]))

    def get_clue(self, value: bytes, rule: bytes) -> Optional[AbstractClueValue]:
        clue_code = bytearray()
        try:
            clue_code.extend(rule)
            clue_code.extend(b'|')
            clue_code.extend(value)
            return get_value(self.pos, rule.decode("ascii"), ImmutableDict({
                "old_style": True,
                "type": b64encode(rule).decode(),
                "code": b64encode(value).decode()
            }))
        except:
            return VALUE_QUESS

    def create_constraints(self, board: AbstractBoard, switch):
        clue1 = self.get_clue(self.value[0], self.rule[0])
        clue2 = self.get_clue(self.value[1], self.rule[1])

        clue3 = self.get_clue(self.value[0], self.rule[1])
        clue4 = self.get_clue(self.value[1], self.rule[0])

        model = board.get_model()
        s = switch.get(model, self)

        select1 = model.new_bool_var(f"BIN_select1_{self.pos}")
        select2 = model.new_bool_var(f"BIN_select2_{self.pos}")
        model.add(select1 == 0).OnlyEnforceIf(s.Not())
        model.add(select2 == 0).OnlyEnforceIf(s.Not())
        model.add(sum([select1, select2]) == 1).OnlyEnforceIf(s)

        clue1.create_constraints(board, FakeSwitch(select1))
        clue2.create_constraints(board, FakeSwitch(select1))

        clue3.create_constraints(board, FakeSwitch(select2))
        clue4.create_constraints(board, FakeSwitch(select2))
