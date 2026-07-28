from typing import Dict, List

from minesweepervariants.board import Board, Position, Size
from minesweepervariants.impl.summon.solver import Switch

from . import AbstractClueSharp
from ....abs.Rrule import AbstractClueValue
from ....impl.impl_obj import get_rule, get_value
from ....utils.image_template import get_col, get_dummy, get_text
from ....utils.impl_obj import VALUE_CIRCLE, VALUE_CROSS, VALUE_QUESS
from ....utils.tool import get_logger, get_random
from ....utils.web_template import Number

main_rules = ["V", "1M", "1L", "1N", "1X", "1P", "1E", "1X'", "1K", "1W'", "2D", "2M", "2X'"]

NAME_2EC = "2EC#"
NAME_2EC_VALUE = "2E"
NAME_2EC_RULE = "C#"
VALUE_LABELS = "ABCDEFGHI"


class Rule2ECSharp(AbstractClueSharp):
    id = "2EC#"
    name = "Encrypted Value + Encrypted Tag"
    name.zh_CN = "加密数值 + 加密标签"
    doc = (
        "Clue values and clue tags are both encrypted by the 2EC sub-board.\n"
        "Specify the rules used and their order through 2EC#:<rule1>;<rule2>;...\n"
        "Only rules whose clues use SingleIntValue are supported.\n"
    )
    doc.zh_CN = (
        "线索数值和线索标签都会通过 2EC 副板加密。\n"
        "通过 2EC#:<rule1>;<rule2>;... 指定使用的规则及其顺序。\n"
        "仅支持线索值使用 SingleIntValue 的规则。\n"
    )
    tags = ["Creative", "Local", "Extensive Trial"]
    creation_time = "2026-07-26"
    author = ("", 0)

    def __init__(self, board: Board = None, data: str=None) -> None:
        single_board = True
        if data is not None and data.startswith('!;'):
            data = data[2:]
            single_board= False
        self.single_board = single_board

        if not data:
            size = board.boundary().x + 1
            valid = [rule for rule in main_rules if hasattr(get_rule(rule), "fill")]
            self.rules = get_random().sample(valid, k=min(size, len(valid)))
        else:
            self.rules = data.split(";")
        super().__init__(self.rules, board)
        get_logger().info(f"Init 2EC# with rules {self.rules}")
        size = max(min(board.boundary().x + 1, len(VALUE_LABELS)), len(self.rules))
        value_labels = [str(i) for i in range(size)]

        if self.single_board:
            labels_dict = self._pack_labels_dict(size)
            board.generate_board(NAME_2EC, size=Size(size, size), labels=labels_dict)
            board.set_config(NAME_2EC, "pos_label", True)
        else:
            board.generate_board(NAME_2EC_VALUE, size=Size(size, size), labels=value_labels)
            board.set_config(NAME_2EC_VALUE, "pos_label", True)

            board.generate_board(NAME_2EC_RULE, size=Size(len(self.rules), len(self.rules)), labels=self.rules)
            board.set_config(NAME_2EC_RULE, "pos_label", True)

        for key in board.get_interactive_keys():
            board.set_config(key, "by_mini", True)

    @classmethod
    def label_x(cls, x: int) -> str:
        if x < len(VALUE_LABELS):
            return VALUE_LABELS[x]
        return chr(96 + x // 26) + chr(97 + x % 26)

    def _pack_labels_dict(self, size: int) -> dict[Position, str]:
        rule_objs = [get_rule(r) for r in self.rules]
        labels_dict: dict[Position, str] = {}
        for row in range(size):
            rname = getattr(rule_objs[row], 'id', '') if row < len(rule_objs) else ''
            for col in range(size):
                p = Position(col, row, NAME_2EC)
                if rname:
                    labels_dict[p] = f"{chr(65 + col)}={row}\n{chr(65 + col)}={rname}"
                else:
                    labels_dict[p] = f"{chr(65 + col)}={row}\n"
        return labels_dict

    @staticmethod
    def _unpack_rule_names(labels_dict: dict) -> list[str]:
        rule_map: dict[int, str] = {}
        for pos, text in labels_dict.items():
            lines = text.split("\n")
            for line in lines:
                if "=" in line:
                    _, right = line.split("=", 1)
                    right = right.strip()
                    if right and not right.isdigit():
                        rule_map[pos.row] = right
        return [rule_map[i] for i in sorted(rule_map)]

    def fill(self, board: Board) -> Board:
        self.init_clear(board)
        random = get_random()
        value_size = board.boundary(key=NAME_2EC if self.single_board else NAME_2EC_VALUE).x + 1
        value_columns = [i for i in range(value_size)]
        rule_columns = [i for i in range(len(self.rules))]
        random.shuffle(value_columns)
        if self.single_board:
            rule_columns = value_columns[: len(rule_columns)]
        else:
            random.shuffle(rule_columns)
        for value, enc in enumerate(value_columns):
            board.set_value(board.get_pos(value, enc, NAME_2EC if self.single_board else NAME_2EC_VALUE), VALUE_CIRCLE)
        if not self.single_board:
            for rule_index, rule_enc in enumerate(rule_columns):
                board.set_value(board.get_pos(rule_index, rule_enc, NAME_2EC_RULE), VALUE_CIRCLE)
        for pos, _ in board("N", key=NAME_2EC if self.single_board else NAME_2EC_VALUE):
            board.set_value(pos, VALUE_CROSS)
        if not self.single_board:
            for pos, _ in board("N", key=NAME_2EC_RULE):
                board.set_value(pos, VALUE_CROSS)

        boards: list[Board] = []
        for rule in self.shape_rule.rules:
            if hasattr(rule, "fill"):
                boards.append(rule.fill(board.clone()))
        for key in board.get_interactive_keys():
            for pos, _ in board("N", key=key):
                clues = [_board.get_value(pos) for _board in boards]
                candidate_indices = [i for i, clue in enumerate(clues) if clue is not None]
                if not candidate_indices:
                    board.set_value(pos, VALUE_QUESS)
                    continue
                rule_index = random.choice(candidate_indices)
                clue = clues[rule_index]
                value = self.get_clue_number(clue)
                if value >= len(value_columns):
                    board.set_value(pos, VALUE_QUESS)
                    continue
                board.set_value(
                    pos,
                    Value2ECSharp(
                        pos,
                        value=value,
                        enc=value_columns[value],
                        rule_enc=rule_columns[rule_index],
                        single_board=self.single_board,
                    ),
                )
        return board

    def create_constraints(self, board: Board, switch):
        model = board.get_model()
        s_row = switch.get(model, self, "↔")
        s_col = switch.get(model, self, "↕")
        if self.single_board:
            self.create_permutation_constraints(board, NAME_2EC, s_row, s_col)
        else:
            self.create_permutation_constraints(board, NAME_2EC_VALUE, s_row, s_col)
            self.create_permutation_constraints(board, NAME_2EC_RULE, s_row, s_col)

    def create_permutation_constraints(self, board: Board, key: str, s_row, s_col):
        model = board.get_model()
        bound = board.boundary(key=key)
        for pos in board.get_row_pos(bound):
            var = board.batch(board.get_col_pos(pos), mode="variable")
            model.Add(sum(var) == 1).OnlyEnforceIf(s_col)
        for pos in board.get_col_pos(bound):
            var = board.batch(board.get_row_pos(pos), mode="variable")
            model.Add(sum(var) == 1).OnlyEnforceIf(s_row)

    def init_clear(self, board: Board):
        if self.single_board:
            for pos, _ in board(key=NAME_2EC):
                board.set_value(pos, None)
        else:
            for pos, _ in board(key=NAME_2EC_VALUE):
                board.set_value(pos, None)
            for pos, _ in board(key=NAME_2EC_RULE):
                board.set_value(pos, None)

    def get_clue_number(self, clue: AbstractClueValue) -> int:
        v = getattr(clue, "value", None)
        if v is not None and hasattr(v, "value") and not isinstance(v, int):
            return int(v.value)
        raise TypeError(
            f"2EC# requires SingleIntValue, but {clue.__class__.__name__} "
            f"(id={getattr(clue, 'id', '?')}) does not use it"
        )


class Value2ECSharp(AbstractClueValue):
    id = Rule2ECSharp.id

    def __init__(
        self,
        pos: Position,
        value: int | bytes = 0,
        enc: int = 0,
        rule_enc: int = 0,
        code: bytes = None,
        single_board: bool = True,
    ) -> None:
        super().__init__(pos)
        if isinstance(value, (bytes, bytearray)) and len(value) >= 3:
            self.value = value[0]
            self.enc = value[1]
            self.rule_enc = value[2]
            self.single_board = len(value) < 4 or bool(value[3])
        elif code and isinstance(code, (bytes, bytearray)) and len(code) >= 3:
            self.value = code[0]
            self.enc = code[1]
            self.rule_enc = code[2]
            self.single_board = len(code) < 4 or bool(code[3])
        else:
            self.value = int(value)
            self.enc = int(enc)
            self.rule_enc = int(rule_enc)
            self.single_board = single_board

    def __repr__(self):
        return Rule2ECSharp.label_x(self.enc)

    @classmethod
    def type(cls) -> bytes:
        return Rule2ECSharp.id.encode("ascii")

    def code(self) -> bytes:
        return bytes([int(self.value), int(self.enc), int(self.rule_enc), 1 if self.single_board else 0])

    def compose(self, board) -> Dict:
        return get_col(
            get_dummy(height=0.3),
            get_text(self.get_value_text(board)),
            get_dummy(height=0.3),
        )

    def web_component(self, board) -> Dict:
        return Number(self.get_value_text(board))

    def tag(self, board: Board) -> bytes:
        rule = self.get_decoded_rule(board)
        if rule:
            return rule.encode("ascii")
        return Rule2ECSharp.label_x(self.rule_enc).encode("ascii")

    def high_light(self, board: Board) -> List[Position] | None:
        positions: set[Position] = set()
        for rule in self.get_possible_rules(board):
            for value in self.get_possible_values(board):
                high_light = self.get_clue(rule, value).high_light(board)
                if high_light is not None:
                    positions.update(high_light)
        return list(positions)

    def _rules_from_labels(self, board: Board) -> list[str]:
        board_key = NAME_2EC if self.single_board else NAME_2EC_RULE
        labels = board.get_config(board_key, "labels")
        if isinstance(labels, dict):
            return Rule2ECSharp._unpack_rule_names(labels)
        return labels

    def create_constraints(self, board: Board, switch):
        board_key = NAME_2EC if self.single_board else NAME_2EC_RULE
        rules = self._rules_from_labels(board)
        model = board.get_model()
        s = switch.get(model, self)

        value_line = board.batch(
            board.get_col_pos(board.get_pos(0, self.enc, NAME_2EC if self.single_board else NAME_2EC_VALUE)),
            mode="variable",
        )
        temp_list = []
        for value_index in range(len(value_line)):
            for rule_index, rule in enumerate(rules):
                temp = model.NewBoolVar(f"2EC_temp_{self.pos}_{value_index}_{rule_index}")
                rule_var = board.get_variable(board.get_pos(rule_index, self.rule_enc, NAME_2EC if self.single_board else NAME_2EC_RULE))
                model.AddBoolAnd([value_line[value_index], rule_var, s]).OnlyEnforceIf(temp)
                model.AddBoolOr([
                    value_line[value_index].Not(),
                    rule_var.Not(),
                    s.Not(),
                ]).OnlyEnforceIf(temp.Not())
                self.get_clue(rule, value_index).create_constraints(board, FakeSwitch(temp))
                temp_list.append(temp)
        if temp_list:
            model.Add(sum(temp_list) == 1).OnlyEnforceIf(s)

    def get_value_text(self, board: Board) -> str:
        line = board.batch(
            board.get_col_pos(board.get_pos(0, self.enc, NAME_2EC if self.single_board else NAME_2EC_VALUE)),
            mode="type",
        )
        if "F" in line:
            return str(line.index("F"))
        return Rule2ECSharp.label_x(self.enc)

    def get_decoded_rule(self, board: Board) -> str:
        line = board.batch(
            board.get_col_pos(board.get_pos(0, self.rule_enc, NAME_2EC if self.single_board else NAME_2EC_RULE)),
            mode="type",
        )
        if "F" in line:
            rules = self._rules_from_labels(board)
            return rules[line.index("F")]
        return ""

    def get_possible_values(self, board: Board) -> list[int]:
        line = board.batch(
            board.get_col_pos(board.get_pos(0, self.enc, NAME_2EC if self.single_board else NAME_2EC_VALUE)),
            mode="type",
        )
        return [index for index, item in enumerate(line) if item in {"N", "F"}]

    def get_possible_rules(self, board: Board) -> list[str]:
        line = board.batch(
            board.get_col_pos(board.get_pos(0, self.rule_enc, NAME_2EC if self.single_board else NAME_2EC_RULE)),
            mode="type",
        )
        rules = self._rules_from_labels(board)
        return [rule for index, rule in enumerate(rules) if line[index] in {"N", "F"}]

    def get_clue(self, rule: str, value: int) -> AbstractClueValue:
        from minesweepervariants.utils.value_template import SingleIntValue

        clue = get_value(self.pos, rule, SingleIntValue(value).json())
        if clue is None:
            raise TypeError(
                f"2EC# cannot reconstruct clue for rule '{rule}' "
                f"(id={self.id}) — check that the rule uses SingleIntValue format"
            )
        return clue


class FakeSwitch(Switch):
    def __init__(self, var) -> None:
        self.var = var
        super().__init__()

    def get(self, model, obj, index=None):
        return self.var
