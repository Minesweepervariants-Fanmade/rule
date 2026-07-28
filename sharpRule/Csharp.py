from typing import Dict, List
from minesweepervariants.board import Board, Size
from . import AbstractClueSharp
from minesweepervariants.impl.summon.solver import Switch
from ....utils.tool import get_random, get_logger
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position
from ....utils.impl_obj import VALUE_CIRCLE, VALUE_CROSS
from ....impl.impl_obj import get_value, get_rule
from ....utils.image_template import get_text, get_image, get_dummy, get_col
from ....utils.web_template import Number

main_rules = ["V", "1M", "1L", "1N", "1X", "1P", "1E", "1X'", "1K", "1W'", "2D", "2M", "2X'"]

NAME_C_SHARP = "C#"


class RuleCSharp(AbstractClueSharp):
    id = "C#"
    name = "Encrypted Tag"
    name.zh_CN = "加密标签"
    doc = ("Clues are replaced by letters, each letter corresponds to a clue, and each clue corresponds to a letter\n"
           "Specify the rules used and their order through C#:<rule1>;<rule2>;...\n"
              "By default, the following rules are included and randomly selected in order:\n"
                "V, 1M, 1L, 1N, 1X, 1P, 1E, 1X', 1K, 1W', 2D, 2M, 2X'\n")

    doc.zh_CN = ("标签被字母所取代，每个字母对应一个标签，且每个标签对应一个字母\n"
                    "通过C#:<rule1>;<rule2>;...来指定使用的规则及其顺序\n"
                    "默认包含以下规则且随机顺序选取：\n"
                    "V, 1M, 1L, 1N, 1X, 1P, 1E, 1X', 1K, 1W', 2D, 2M, 2X'\n")
    tags = ["Creative", "Local", "Extensive Trial"]
    creation_time = "2025-08-31"
    author = ("", 0)

    def __init__(self, board: "Board" = None, data=None) -> None:
        if not data:
            size = board.boundary().x + 1
            from minesweepervariants.abs.Rrule import AbstractClueRule as _ACR
            valid = [r for r in main_rules if hasattr(get_rule(r), 'fill')]
            self.rules = get_random().sample(valid, k=min(size, len(valid)))
        else:
            self.rules = data.split(";")
        super().__init__(self.rules, board)
        get_logger().info(f"Init C# with rules {self.rules}")
        board.generate_board(NAME_C_SHARP, size=Size(len(self.rules), len(self.rules)), labels=self.rules)
        board.set_config(NAME_C_SHARP, "pos_label", True)
        for key in board.get_interactive_keys():
            board.set_config(key, "by_mini", True)

    @classmethod
    def label_x(cls, x: int) -> str:
        return chr(96 + x // 26) if x > 25 else '' + chr(97 + x % 26)

    def label_y(self, y: int) -> str:
        return self.rules[y] if 0 <= y < len(self.rules) else ''

    def fill(self, board: 'Board') -> 'Board':
        self.init_clear(board)
        random = get_random()
        shuffled_nums = [i for i in range(len(self.rules))]
        random.shuffle(shuffled_nums)
        for x, y in enumerate(shuffled_nums):
            pos = board.get_pos(x, y, "C#")
            board.set_value(pos, VALUE_CIRCLE)
        for pos, _ in board("N", key="C#"):
            board.set_value(pos, VALUE_CROSS)

        boards : list[Board] = []
        for rule in self.shape_rule.rules:
            if hasattr(rule, 'fill'):
                boards.append(rule.fill(board.clone()))
        for key in board.get_interactive_keys():
            for pos, _ in board("N", key=key):
                values = [_board.get_value(pos) for _board in boards]
                if not values:
                    continue
                else:
                    rule_index = random.randint(0, len(values) - 1)
                clue = values[rule_index]
                board.set_value(pos, ValueCsharp(pos, value=self.get_clue_number(clue), rule=shuffled_nums[rule_index]))
        return board

    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s_row = switch.get(model, self, '↔')
        s_col = switch.get(model, self, '↕')
        bound = board.boundary(key=NAME_C_SHARP)

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

    def init_clear(self, board: 'Board'):
        for pos, _ in board(key=NAME_C_SHARP):
            board.set_value(pos, None)

    def get_clue_number(self, clue: AbstractClueValue) -> int:
        v = getattr(clue, 'value', None)
        if v is not None and hasattr(v, 'value') and not isinstance(v, int):
            return int(v.value)  # SingleIntValue / SingleNumberValue
        raise TypeError(
            f"C# requires SingleIntValue, but {clue.__class__.__name__} "
            f"(id={getattr(clue, 'id', '?')}) does not use it"
        )


class ValueCsharp(AbstractClueValue):
    id = RuleCSharp.id
    def __init__(self, pos: "Position", value: int | bytes = 0, rule: int = 0, code: bytes = None) -> None:
        super().__init__(pos)
        if isinstance(value, (bytes, bytearray)) and len(value) >= 2:
            self.value = value[0]
            self.rule = value[1]
        elif code and isinstance(code, (bytes, bytearray)) and len(code) >= 2:
            self.value = code[0]
            self.rule = code[1]
        else:
            self.value = int(value)
            self.rule = int(rule)

    def __repr__(self):
        return f"{self.value}_{RuleCSharp.label_x(self.rule)}"

    @classmethod
    def type(cls) -> bytes:
        return "C#".encode("ascii")

    def compose(self, board) -> Dict:
        return get_col(
            get_dummy(height=0.3),
            get_text(str(self.value)),
            get_dummy(height=0.3),
        )

    def web_component(self, board) -> Dict:
        # TODO
        return Number(str(self.value))

    def tag(self, board: Board) -> bytes:
        line = board.batch(board.get_col_pos(
            board.get_pos(0, self.rule, NAME_C_SHARP)
        ), mode="type")
        if "F" in line:
            return board.get_config(NAME_C_SHARP, "labels")[line.index("F")].encode("ascii")
        return RuleCSharp.label_x(self.rule).encode("ascii")

    def code(self) -> bytes:
        return bytes([int(self.value), int(self.rule)])

    def high_light(self, board: Board) -> List[Position] | None:
        positions: set[Position] = set()
        line = board.batch(board.get_col_pos(
            board.get_pos(0, self.rule, NAME_C_SHARP)
        ), mode="type")
        for i, type in enumerate(line):
            rule = board.get_config(NAME_C_SHARP, "labels")[i]
            if type == 'N':
                high_light = self.get_clue(rule).high_light(board)
                if high_light is not None:
                    positions.update(high_light)
            elif type == 'F':
                return self.get_clue(rule).high_light(board)
        return list(positions)


    def create_constraints(self, board: 'Board', switch):
        rules: list[str] = board.get_config(NAME_C_SHARP, "labels")
        s = switch.get(board.get_model(), self)
        model = board.get_model()
        temp_list = []
        for i, rule in enumerate(rules):
            clue: AbstractClueValue = self.get_clue(rule)
            temp = model.NewBoolVar(f"temp_{self.pos}_{rule}")
            model.Add(temp == 1).OnlyEnforceIf(
                [board.get_variable(board.get_pos(i, self.rule, NAME_C_SHARP)), s]
            )
            clue.create_constraints(board, FakeSwitch(temp))
            temp_list.append(temp)
        if temp_list:
            model.Add(sum(temp_list) == 1).OnlyEnforceIf(s)

    def get_clue(self, rule: str) -> AbstractClueValue:
        from minesweepervariants.utils.value_template import SingleIntValue
        data = SingleIntValue(self.value).json()
        clue = get_value(self.pos, rule, data)
        if clue is None:
            raise TypeError(
                f"C# cannot reconstruct clue for rule '{rule}' "
                f"(id={self.id}) — check that the rule uses SingleIntValue format"
            )
        return clue


class FakeSwitch(Switch):
    def __init__(self, var) -> None:
        self.var = var
        super().__init__()

    def get(self, model, obj, index=None):
        return self.var
