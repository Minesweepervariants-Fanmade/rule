from typing import Dict
from minesweepervariants.abs.board import AbstractBoard
from . import AbstractClueSharp
from minesweepervariants.impl.summon.solver import Switch
from ....utils.tool import get_random, get_logger
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition
from ....utils.impl_obj import VALUE_CIRCLE, VALUE_CROSS
from ....impl.impl_obj import get_value
from ....utils.image_create import get_text, get_image, get_dummy, get_col
from ....utils.web_template import Number

main_rules = ["V", "1M", "1L", "1N", "1X", "1P", "1E", "1X'", "1K", "1W'", "2D", "2M", "2X'"]

NAME_C_SHARP = "C#"


class RuleCSharp(AbstractClueSharp):
    name = ["C#", "加密标签", "Encrypted Tag"]
    doc = ("标签被字母所取代，每个字母对应一个线索，且每个标签对应一个字母\n"
              "通过C#:<rule1>;<rule2>;...来指定使用的规则及其顺序\n"
              "默认包含以下规则且随机顺序选取：\n"
              "V, 1M, 1L, 1N, 1X, 1P, 1E, 1X', 1K, 1W', 2D, 2M, 2X'\n")

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        if not data:
            size = board.boundary().x + 1
            self.rules = get_random().sample(main_rules, k=min(size, len(main_rules)))
        else:
            self.rules = data.split(";")
        super().__init__(self.rules, board)
        get_logger().info(f"Init C# with rules {self.rules}")
        board.generate_board(NAME_C_SHARP, size=(len(self.rules), len(self.rules)), labels=self.rules)
        board.set_config(NAME_C_SHARP, "pos_label", True)
        for key in board.get_interactive_keys():
            board.set_config(key, "by_mini", True)

    @classmethod
    def label_x(cls, x: int) -> str:
        return chr(96 + x // 26) if x > 25 else '' + chr(97 + x % 26)

    def label_y(self, y: int) -> str:
        return self.rules[y] if 0 <= y < len(self.rules) else ''
    
    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        random = get_random()
        shuffled_nums = [i for i in range(len(self.rules))]
        random.shuffle(shuffled_nums)
        for x, y in enumerate(shuffled_nums):
            pos = board.get_pos(x, y, "C#")
            board.set_value(pos, VALUE_CIRCLE)
        for pos, _ in board("N", key="C#"):
            board.set_value(pos, VALUE_CROSS)
        
        boards : list[AbstractBoard] = []
        for rule in self.shape_rule.rules:
            boards.append(rule.fill(board.clone()))
        for key in board.get_board_keys():
            for pos, _ in board("N", key=key):
                values = [_board.get_value(pos) for _board in boards]
                if not values:
                    continue
                else:
                    rule_index = random.randint(0, len(values) - 1)
                    clue = values[rule_index]
                    clue_type = clue.type().decode("utf-8", "ignore")
                    board.set_value(pos, ValueCsharp(pos, value=self.get_clue_number(clue), rule=shuffled_nums[rule_index]))
        return board
    
    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        bound = board.boundary(key=NAME_C_SHARP)

        row = board.get_row_pos(bound)
        for pos in row:
            line = board.get_col_pos(pos)
            var = board.batch(line, mode="variable")
            model.Add(sum(var) == 1).OnlyEnforceIf(s)

        col = board.get_col_pos(bound)
        for pos in col:
            line = board.get_row_pos(pos)
            var = board.batch(line, mode="variable")
            model.Add(sum(var) == 1).OnlyEnforceIf(s)

    def init_clear(self, board: 'AbstractBoard'):
        for pos, _ in board(key=NAME_C_SHARP):
            board.set_value(pos, None)
    
    def get_clue_number(self, clue: AbstractClueValue) -> int:
        try:
            return clue.value
        except AttributeError:
            try:
                return clue.count
            except AttributeError:
                raise RuntimeError("Unsupported clue " + clue.type().decode("utf-8", "ignore"))


class ValueCsharp(AbstractClueValue):
    def __init__(self, pos: "AbstractPosition", value: int = 0, rule: int = 0, code: bytes = None) -> None:
        super().__init__(pos)
        if not code:
            self.value = value
            self.rule = rule
        else:
            self.value = code[0]
            self.rule = code[1]

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
    
    def tag(self, board) -> bytes:
        return RuleCSharp.label_x(self.rule).encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value, self.rule])
    
    def create_constraints(self, board: 'AbstractBoard', switch):
        rules: list[str] = board.get_config(NAME_C_SHARP, "labels")
        s = switch.get(board.get_model(), self)
        model = board.get_model()
        temp_list = []
        for i, rule in enumerate(rules):
            clue_code = bytearray()
            clue_code.extend(rule.encode("ascii"))
            clue_code.extend(b'|')
            clue_code.extend(bytes([self.value]))
            clue: AbstractClueValue = get_value(self.pos, bytes(clue_code))
            temp = model.NewBoolVar(f"temp_{self.pos}_{rule}")
            model.Add(temp == 1).OnlyEnforceIf(
                [board.get_variable(board.get_pos(i, self.rule, NAME_C_SHARP)), s]
            )
            clue.create_constraints(board, FakeSwitch(temp))
            temp_list.append(temp)
        model.Add(sum(temp_list) == 1).OnlyEnforceIf(s)


class FakeSwitch(Switch):
    def __init__(self, var) -> None:
        self.var = var
        super().__init__()

    def get(self, model, obj, index=None):
        return self.var
