from typing import Dict, List
from importlib import import_module
from minesweepervariants.board import Board, Size
from minesweepervariants.immutable_dict import ImmutableDict
from . import AbstractClueSharp
from minesweepervariants.impl.summon.solver import Switch
from ....utils.tool import get_random, get_logger
from ....abs.Rrule import AbstractClueValue
from minesweepervariants.board import Board, Position
from ....utils.impl_obj import VALUE_CIRCLE, VALUE_CROSS, VALUE_QUESS
from ....impl.impl_obj import get_value
from ....utils.image_template import get_text, get_image, get_dummy, get_col, get_row
from ....utils.web_template import Number, MultiNumber, StrWithArrow

from base64 import b64encode

NAME_2EC = "2EC"
NAME_RULE = "C"
rule2P = import_module("minesweepervariants.impl.rule.Rrule.2P")

class Rule2ECSharp(AbstractClueSharp):
    id = "2EC#"
    name = "Encrypted + Encrypted Tag"
    name.zh_CN = "加密 + 加密标签"
    doc = ("Clues are replaced by letters, each letter corresponds to a clue, and each clue corresponds to a letter\n"
                "Specify the rules used and their order through 2EC#:<rule1>;<rule2>;...\n"
                "Combines the encrypted complexity of 2E# with the simpler tag system of C#\n"
                "You can add 1# 1#' 2# 2#' 2#':\n")
    doc.zh_CN = ("线索被字母所取代，每个字母对应一个线索，且每个线索对应一个字母\n"
              "通过2EC#:<rule1>;<rule2>;...来指定使用的规则及其顺序\n"
              "结合了2E#的加密复杂性和C#的简化标签系统\n"
              "可添加 1# 1#' 2# 2#' 2#':\n")
    tags = ["Original", "Local", "Extensive Trial"]
    creation_time = "2026-07-25"
    author = ("NT", 2201963934)

    def __init__(self, board: "Board" = None, data=None) -> None:
        self.rules = []
        _seen = set()
        def _add(r):
            if r not in _seen:
                self.rules.append(r)
                _seen.add(r)
        if not data:
            for r in ["V", "1M", "1L", "1N", "1X", "1P", "1E", "1X'", "1K", "1W'", "2X'", "2X", "2D", "2P", "2M", "2A"]:
                _add(r)
        else:
            for rule in data.split(";"):
                if rule == "1#":
                    for r in ["V", "1M", "1L", "1W", "1N", "1X", "1P", "1E"]:
                        _add(r)
                elif rule == "1#'":
                    for r in ["V", "1M", "1L", "1W", "1N", "1X", "1P", "1E", "1X'", "1K", "1W'", "1E'", "1L1M", "1M1N", "1M1X", "1N1X"]:
                        _add(r)
                elif rule == "2#":
                    for r in ["V", "2X", "2D", "2P", "2M", "2A"]:
                        _add(r)
                elif rule == "2#'":
                    for r in ["V", "2X", "2D", "2P", "2M", "2A", "2X'"]:
                        _add(r)
                elif rule == "2#':":
                    for r in ["V", "2X", "2D", "2P", "2M", "2X'"]:
                        _add(r)
                else:
                    _add(rule)
        pos = board.boundary()
        size = min(pos.x + 1, 9)
        if len(self.rules) > size:
            self.rules = get_random().sample(list(self.rules), k=size)
        super().__init__(self.rules, board)
        pos = board.boundary()
        size = min(pos.x + 1, 9)
        board.generate_board(NAME_2EC, Size(size, size))
        board.generate_board(NAME_RULE, Size(size, size))
        for key in board.get_interactive_keys():
            board.set_config(key, "by_mini", True)

    def fill(self, board: 'Board') -> 'Board':
        self.init_clear(board)
        random = get_random()
        fill_rules = [r for r in self.shape_rule.rules if hasattr(r, 'fill')]
        size = min(9, board.boundary().x + 1)
        ns = min(size, len(fill_rules))
        shuffled_nums = [i for i in range(size)]
        shuffled_rules = [i for i in range(ns)]
        random.shuffle(shuffled_nums)
        random.shuffle(shuffled_rules)
        for x, y in enumerate(shuffled_nums):
            pos = board.get_pos(x, y, NAME_2EC)
            board.set_value(pos, VALUE_CIRCLE)

        for pos, _ in board("N", key=NAME_2EC):
            board.set_value(pos, VALUE_CROSS)

        # Rule encryption sub-board (like C#)
        for x, y in enumerate(shuffled_rules):
            pos = board.get_pos(x, y, NAME_RULE)
            board.set_value(pos, VALUE_CIRCLE)

        for pos, _ in board("N", key=NAME_RULE):
            board.set_value(pos, VALUE_CROSS)

        boards: list[Board] = []
        boards = [r.fill(board.clone()) for r in fill_rules]
        labels_dict = {}
        rule_labels = {}
        for row in range(size):
            rule_index = shuffled_rules.index(row) if row in shuffled_rules else -1
            rname = getattr(fill_rules[rule_index], 'id', '') if rule_index >= 0 else ''
            for col in range(size):
                p = Position(col, row, NAME_2EC)
                if rname:
                    labels_dict[p] = f"{chr(65 + col)}={row}\n{chr(97 + row)}={rname}"

        # Rule sub-board labels: only at O positions
        for ci in range(ns):
            ri = shuffled_rules[ci] if ci < len(shuffled_rules) else -1
            if 0 <= ri < len(fill_rules):
                rname = getattr(fill_rules[ri], 'id', '')
                if rname:
                    rp = Position(ci, ri, NAME_RULE)
                    rule_labels[rp] = f"{chr(97 + ci)}={rname}"
        board.set_config(NAME_2EC, "labels", labels_dict)
        board.set_config(NAME_2EC, "pos_label", True)
        board.set_config(NAME_RULE, "labels", rule_labels)
        board.set_config(NAME_RULE, "pos_label", True)

        for pos, _ in board("N"):
            valid = []
            for rule_idx, _board in enumerate(boards):
                clue = _board.get_value(pos)
                if clue is None:
                    continue
                val = self._extract_val(clue)
                if val is not None and val in shuffled_nums:
                    type = getattr(clue, 'id', '') or getattr(clue, 'type', lambda: b'')().decode("ascii", "ignore")
                    valid.append((rule_idx, type, val))

            if valid:
                rule_idx, type, val = random.choice(valid)
                e_col = shuffled_nums.index(val)
                rule_enc = shuffled_rules[rule_idx]
                board.set_value(pos, Value2ECSharp(pos, value=val, rule=type, enc=e_col, rule_enc=rule_enc))
            else:
                board.set_value(pos, VALUE_QUESS)

        return board

    @staticmethod
    def _extract_val(clue):
        v = getattr(clue, 'value', None)
        if v is not None and hasattr(v, 'value') and not isinstance(v, int):
            return int(v.value)
        try:
            return int(getattr(clue, 'count', ''))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _can_encrypt(clue):
        return Rule2ECSharp._extract_val(clue) is not None

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s_row = switch.get(model, self, '↔')
        s_col = switch.get(model, self, '↕')
        bound = board.boundary(key=NAME_2EC)

        row = board.get_row_pos(bound)
        for pos in row:
            line = board.get_col_pos(pos)
            var = board.batch(line, mode="variable")
            model.Add(sum(var) == 1).OnlyEnforceIf(s_col)

        col = board.get_col_pos(bound)
        for pos in col:
            line = board.get_row_pos(pos)
            var = board.batch(line, mode="variable")
            model.Add(sum(var) == 1).OnlyEnforceIf(s_row)

        # Rule sub-board constraints
        bound_r = board.boundary(key=NAME_RULE)
        row_r = board.get_row_pos(bound_r)
        for pos in row_r:
            line = board.get_col_pos(pos)
            var = board.batch(line, mode="variable")
            model.Add(sum(var) == 1).OnlyEnforceIf(s_col)

        col_r = board.get_col_pos(bound_r)
        for pos in col_r:
            line = board.get_row_pos(pos)
            var = board.batch(line, mode="variable")
            model.Add(sum(var) == 1).OnlyEnforceIf(s_row)

    def init_clear(self, board: 'Board'):
        for pos, _ in board(key=NAME_2EC):
            board.set_value(pos, None)
        for pos, _ in board(key=NAME_RULE):
            board.set_value(pos, None)


class Value2ECSharp(AbstractClueValue):
    id = Rule2ECSharp.id
    def __init__(self, pos: Position, value: int = 0, rule: str = '', rule_idx: int = 0, shuffled_rule: int = 0, enc: int = 0, rule_enc: int | None = None, code: bytes = None) -> None:
        super().__init__(pos)
        if isinstance(value, (bytes, bytearray)):
            self.enc = value[0] if len(value) >= 1 else 0
            self.rule_enc = value[1] if len(value) >= 2 else 0
            self.value = value[2] if len(value) >= 3 else 0
            self.rule = value[3:].decode("ascii", "ignore") if len(value) >= 4 else ''
        elif code and isinstance(code, (bytes, bytearray)):
            self.enc = code[0] if len(code) >= 1 else 0
            self.rule_enc = code[1] if len(code) >= 2 else 0
            self.value = code[2] if len(code) >= 3 else 0
            self.rule = code[3:].decode("ascii", "ignore") if len(code) >= 4 else ''
        else:
            self.value = int(value)
            self.rule = rule
            self.enc = enc
            self.rule_enc = rule_enc if rule_enc is not None else (shuffled_rule or rule_idx)
        self.rule_idx = self.rule_enc
        self.shuffled_rule = self.rule_enc

    def __str__(self) -> str:
        return f"{'ABCDEFGHI'[self.enc]}{chr(97 + self.rule_enc % 26)}"

    def web_component(self, board) -> Dict:
        line = board.batch(board.get_col_pos(board.get_pos(0, self.enc, NAME_2EC)), mode="type")
        if "F" in line:
            return Number(str(line.index("F")))
        return Number("ABCDEFGHI"[self.enc])

    def compose(self, board) -> Dict:
        line = board.batch(board.get_col_pos(board.get_pos(0, self.enc, NAME_2EC)), mode="type")
        if "F" in line:
            return get_col(get_dummy(height=0.3), get_text(str(line.index("F"))), get_dummy(height=0.3))
        return get_col(get_dummy(height=0.3), get_text("ABCDEFGHI"[self.enc]), get_dummy(height=0.3))

    def high_light(self, board: 'Board') -> List['Position'] | None:
        return self.get_clue(self.rule).high_light(board)

    @classmethod
    def type(cls) -> bytes:
        return Rule2ECSharp.id.encode("ascii")

    def code(self) -> bytes:
        return bytes([self.enc, self.rule_enc, self.value]) + self.rule.encode("ascii")

    def tag(self, board) -> bytes:
        line = board.batch(board.get_col_pos(board.get_pos(0, self.rule_enc, NAME_RULE)), mode="type")
        if "F" in line:
            return self.rule.encode("ascii")
        return chr(97 + self.rule_enc % 26).encode("ascii")

    def create_constraints(self, board: 'Board', switch):
        """Value decryption via sub-board column (like 2E#); rule used directly from self.rule."""
        model = board.get_model()
        s = switch.get(model, self)

        temp_list = []
        value_line = board.batch(board.get_col_pos(board.get_pos(0, self.enc, NAME_2EC)), mode="variable")
        for value_index, value_var in enumerate(value_line):
            temp = model.NewBoolVar(f"temp_{self.pos}_{value_index}")
            model.Add(temp == 1).OnlyEnforceIf([value_var, s])
            clue = self.get_clue(self.rule, value_index)
            if clue is None:
                continue
            clue.create_constraints(board, FakeSwitch(temp))
            temp_list.append(temp)
        if temp_list:
            model.Add(sum(temp_list) == 1).OnlyEnforceIf(s)

    def get_clue(self, rule: str, value: int | None = None) -> AbstractClueValue:
        from minesweepervariants.utils.value_template import SingleIntValue
        clue_value = self.value if value is None else value
        return get_value(self.pos, rule, SingleIntValue(clue_value).json())

class Value2EC2A(Value2ECSharp):
    id = "2EC2A"
    def __init__(self, pos: Position, value: int = 0, code: bytes = None, flag = 4) -> None:
        super().__init__(pos, value, '2A', code)
        self.flag = flag

    @classmethod
    def type(cls):
        return "2EC2A".encode("ascii")

    def get_clue(self, value) -> AbstractClueValue:
        from minesweepervariants.utils.value_template import SingleIntValue
        return get_value(self.pos, self.rule, SingleIntValue(value).json())


class Value2EC2X(AbstractClueValue):
    id = "2EC2X"
    def __init__(self, pos: 'Position', count: int = 0, code: bytes = None):
        super().__init__(pos, code)
        if isinstance(count, (bytes, bytearray)) and len(count) >= 1:
            self.count = count[0]
        elif code is not None:
            self.count = code[0]
        else:
            self.count = count
        self.neighbor = self.pos.neighbors(2)

    def __repr__(self) -> str:
        map = "ABCDEFGHI"
        return f"{map[self.count // 10]} {map[self.count % 10]}"

    def high_light(self, board: 'Board') -> list['Position']:
        return self.neighbor

    @classmethod
    def type(cls) -> bytes:
        return "2EC2X".encode("ascii")

    def code(self) -> bytes:
        return bytes([self.count])

    def tag(self, board) -> bytes:
        return "2X".encode("ascii")

    def compose(self, board) -> Dict:
        text_a, text_b = self.get_display_text(board)
        return get_row(
            get_text(text_a),
            get_text(text_b)
        )

    def web_component(self, board) -> Dict:
        text_a, text_b = self.get_display_text(board)
        return MultiNumber([text_a, text_b])

    def get_display_text(self, board) -> list[str]:
        map = "ABCDEFGHI"
        values = [self.count // 10, self.count % 10]
        lines = [board.batch(board.get_col_pos(
            board.get_pos(0, v, NAME_2EC)
        ), mode="type") for v in values]
        texts = [(str(l.index("F")) if "F" in l else map[v]) for l, v in zip(lines, values)]
        texts.sort()
        return texts

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)

        line_a = board.batch(board.get_col_pos(
            board.get_pos(0, self.count // 10, NAME_2EC)
        ), mode="variable")
        line_b = board.batch(board.get_col_pos(
            board.get_pos(0, self.count % 10, NAME_2EC)
        ), mode="variable")

        # 收集周围格子的布尔变量
        neighbor_vars1 = []
        neighbor_vars2 = []
        for neighbor in self.neighbor:  # 8方向相邻格子
            if board.in_bounds(neighbor):
                if board.get_dyed(neighbor):
                    var = board.get_variable(neighbor)
                    neighbor_vars1.append(var)
                else:
                    var = board.get_variable(neighbor)
                    neighbor_vars2.append(var)

        if neighbor_vars1 or neighbor_vars2:
            # 定义变量
            t = model.NewBoolVar('t')
            for a in range(len(line_a)):
                for b in range(len(line_b)):
                    model.Add(sum(neighbor_vars1) == a).OnlyEnforceIf([line_a[a], t, s])
                    model.Add(sum(neighbor_vars1) != a).OnlyEnforceIf([line_a[a].Not(), t, s])
                    model.Add(sum(neighbor_vars2) == b).OnlyEnforceIf([line_b[b], t, s])
                    model.Add(sum(neighbor_vars2) != b).OnlyEnforceIf([line_b[b].Not(), t, s])

                    model.Add(sum(neighbor_vars1) == b).OnlyEnforceIf([line_b[b], t.Not(), s])
                    model.Add(sum(neighbor_vars1) != b).OnlyEnforceIf([line_b[b].Not(), t.Not(), s])
                    model.Add(sum(neighbor_vars2) == a).OnlyEnforceIf([line_a[a], t.Not(), s])
                    model.Add(sum(neighbor_vars2) != a).OnlyEnforceIf([line_a[a].Not(), t.Not(), s])

class Value2EC2P(AbstractClueValue):
    id = "2EC2P"
    @staticmethod
    def convert_missing_value(x: int) -> int:
        if (x == -1):
            return 254
        elif (x == 254):
            return -1
        else:
            return x

    def __init__(self, pos: 'Position', a: int = -1, b: int = -1, code: bytes = None):
        """
        A√B, -1 为缺失值
        """
        super().__init__(pos)
        if isinstance(a, (bytes, bytearray)) and len(a) >= 2:
            self.value_a = Value2EC2P.convert_missing_value(a[0])
            self.value_b = Value2EC2P.convert_missing_value(a[1])
        elif code and isinstance(code, (bytes, bytearray)) and len(code) >= 2:
            self.value_a = Value2EC2P.convert_missing_value(code[0])
            self.value_b = Value2EC2P.convert_missing_value(code[1])
        else:
            self.value_a = int(a) if a != -1 else -1
            self.value_b = int(b) if b != -1 else -1

    def __repr__(self) -> str:
        map = "ABCDEFGHI"
        r = ''
        if self.value_a != -1:
            r += map[self.value_a]
        if self.value_b != -1:
            r += f"√{map[self.value_b]}"
        return r

    @classmethod
    def type(cls) -> bytes:
        return "2EC2P".encode("ascii")

    def code(self) -> bytes:
        return bytes([Value2EC2P.convert_missing_value(self.value_a), Value2EC2P.convert_missing_value(self.value_b)])

    def tag(self, board) -> bytes:
        return "2P".encode("ascii")

    def compose(self, board) -> Dict:
        value_a, value_b = self.get_display_text(board)
        if value_b is None:
            return get_col(
                get_dummy(height=0.175),
                get_text(str(value_a)),
                get_dummy(height=0.175),
            )
        elif value_a is None:
            return get_row(
                get_image("sqrt"),
                get_text(str(value_b)),
                spacing=-0.15
            )
        else:
            return get_row(
                get_text(str(value_a)),
                get_image("sqrt"),
                get_text(str(value_b)),
                spacing=-0.2
            )

    def web_component(self, board) -> Dict:
        value_a, value_b = self.get_display_text(board)
        if value_b is None:
            return get_text(str(value_a))
        if value_a is None:
            return get_text(
                "$\\sqrt{" + str(value_b) + "}$"
            )
        else:
            return get_text(
                "$" + str(value_a) +
                "\\sqrt{" + str(value_b) +
                "}$"
            )

    def get_display_text(self, board) -> tuple[str | None, str | None]:
        part_a = part_b = None
        map = "ABCDEFGHI"
        if self.value_a != -1:
            line_a = board.batch(board.get_col_pos(
                board.get_pos(0, self.value_a, NAME_2EC)
            ), mode="type")
            part_a = str(line_a.index("F")) if ("F" in line_a) else map[self.value_a]
        if self.value_b != -1:
            line_b = board.batch(board.get_col_pos(
                board.get_pos(0, self.value_b, NAME_2EC)
            ), mode="type")
            if ("F" in line_b):
                num_b = line_b.index("F")
                if (num_b == 1):
                    if not part_a:
                        part_a = "1"
                elif (num_b == 4):
                    if not part_a:
                        part_a = "2"
                    else:
                        if part_a.isdigit():
                            part_a = str(int(part_a) * 2)
                        else:
                            part_a = "2" + part_a
                else:
                    part_b = str(num_b)
            else:
                part_b = map[self.value_b]
        return part_a, part_b

    def create_constraints(self, board: 'Board', switch):
        s = switch.get(board.get_model(), self)
        model = board.get_model()
        if self.value_a != -1 and self.value_b != -1:
            line_a = board.batch(board.get_col_pos(
                board.get_pos(0, self.value_a, NAME_2EC)
            ), mode="variable")
            line_b = board.batch(board.get_col_pos(
                board.get_pos(0, self.value_b, NAME_2EC)
            ), mode="variable")
            for i in range(len(line_a)):
                for j in range(len(line_b)):
                    temp_a = line_a[i]
                    temp_b = line_b[j]
                    temp_ab_combine = model.NewBoolVar(f"2EC2P_temp_a_b_combine_{self.pos}_{i}_{j}")
                    model.AddBoolAnd([temp_a, temp_b, s]).OnlyEnforceIf(temp_ab_combine)
                    model.AddBoolOr([temp_a.Not(), temp_b.Not(), s.Not()]).OnlyEnforceIf(temp_ab_combine.Not())
                    self.create_2P(i * j * j).create_constraints(board, FakeSwitch(temp_ab_combine))
        elif self.value_a != -1:
            line_a = board.batch(board.get_col_pos(
                board.get_pos(0, self.value_a, NAME_2EC)
            ), mode="variable")
            for i in range(len(line_a)):
                temp_a = line_a[i]
                clue_switch = model.NewBoolVar(f"2EC2P_temp_clue_{self.pos}")
                model.AddBoolAnd([temp_a, s]).OnlyEnforceIf(clue_switch)
                model.AddBoolOr([temp_a.Not(), s.Not()]).OnlyEnforceIf(clue_switch.Not())
                self.create_2P(i * i).create_constraints(board, FakeSwitch(clue_switch))
        elif self.value_b != -1:
            line_b = board.batch(board.get_col_pos(
                board.get_pos(0, self.value_b, NAME_2EC)
            ), mode="variable")
            for i in range(len(line_b)):
                temp_b = line_b[i]
                clue_switch = model.NewBoolVar(f"2EC2P_temp_clue_{self.pos}")
                model.AddBoolAnd([temp_b, s]).OnlyEnforceIf(clue_switch)
                model.AddBoolOr([temp_b.Not(), s.Not()]).OnlyEnforceIf(clue_switch.Not())
                self.create_2P(i).create_constraints(board, FakeSwitch(clue_switch))

    def create_2P(self, value):
        if value > 254:
            return rule2P.Value2P(pos=self.pos, code=bytes([value // 255, value % 255]))
        return rule2P.Value2P(pos=self.pos, code=bytes([value]))

class Value2EC1EN(AbstractClueValue):
    id = "2EC1E'"
    # arrow True 上下箭头，False 左右箭头
    def __init__(self, pos: 'Position', value: int = 0, arrow: bool = True, code: bytes = None):
        super().__init__(pos)
        if isinstance(value, (bytes, bytearray)) and len(value) >= 2:
            self.value = value[0]
            self.arrow = value[1] == 1
        elif code and isinstance(code, (bytes, bytearray)) and len(code) >= 2:
            self.value = code[0]
            self.arrow = code[1] == 1
        else:
            self.value = int(value)
            self.arrow = arrow

    def __repr__(self):
        map = "ABCDEFGHI"
        if (self.arrow):
            return f"{map[self.value]}"
        else:
            return f"-{map[self.value]}"

    @classmethod
    def type(cls) -> bytes:
        return "2EC1E'".encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value, 1 if self.arrow else 0])

    def tag(self, board) -> bytes:
        return "1E'".encode("ascii")

    def high_light(self, board: 'Board') -> list['Position'] | None:
        return self.create1EN(0).high_light(board)

    def web_component(self, board) -> Dict:
        line = board.batch(board.get_col_pos(
            board.get_pos(0, self.value, NAME_2EC)
        ), mode="type")
        num = str(line.index("F")) if "F" in line else "ABCDEFGHI"[self.value]

        if num == '0':
            return Number(0)
        if not self.arrow:
            return StrWithArrow(num, "left_right")
        else:
            return StrWithArrow(num, "up_down")

    def compose(self, board):
        line = board.batch(board.get_col_pos(
            board.get_pos(0, self.value, NAME_2EC)
        ), mode="type")
        num = str(line.index("F")) if "F" in line else "ABCDEFGHI"[self.value]

        if num == '0':
            return get_col(
                get_dummy(height=0.3),
                get_text('0'),
                get_dummy(height=0.3),
            )
        if not self.arrow:
            return get_col(
                get_image(
                    "double_horizontal_arrow",
                    image_height=0.4,
                ),
                get_dummy(height=-0.1),
                get_text(num)
            )
        else:
            return get_row(
                    get_dummy(width=0.15),
                    get_image("double_vertical_arrow", ),
                    get_dummy(width=-0.15),
                    get_text(num),
                    get_dummy(width=0.15),
            )

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)

        line = board.batch(board.get_col_pos(
            board.get_pos(0, self.value, NAME_2EC)
        ), mode="variable")

        temp_list = []
        for index in range(len(line)):
            temp = model.NewBoolVar(f"temp_{self.pos}_{index}")
            model.Add(temp == 1).OnlyEnforceIf([line[index], s])
            self.create1EN(index).create_constraints(board, FakeSwitch(temp))
            temp_list.append(temp)
        model.Add(sum(temp_list) == 1).OnlyEnforceIf(s)

    def create1EN(self, value) -> AbstractClueValue:
        clue_code = bytearray()
        clue_code.extend("1E'".encode("ascii"))
        clue_code.extend(b'|')
        if value == 0:
            clue_code.extend(bytes([128]))
        elif self.arrow:
            clue_code.extend(bytes([value + 128]))
        else:
            clue_code.extend(bytes([-value + 128]))
        return get_value(self.pos, self.rule, ImmutableDict({
            "old_style": True,
            "type": b64encode(self.type()).decode(),
            "code": b64encode(int.to_bytes(value)).decode()
        }))


class FakeSwitch(Switch):
    def __init__(self, var) -> None:
        self.var = var
        super().__init__()

    def get(self, model, obj, index=None):
        return self.var
