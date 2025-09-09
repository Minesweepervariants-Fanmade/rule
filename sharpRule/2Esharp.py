from typing import Dict, List
from importlib import import_module
from minesweepervariants.abs.board import AbstractBoard
from . import AbstractClueSharp
from minesweepervariants.impl.summon.solver import Switch
from ....utils.tool import get_random, get_logger
from ....abs.Rrule import AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition
from ....utils.impl_obj import VALUE_CIRCLE, VALUE_CROSS
from ....impl.impl_obj import get_value
from ....utils.image_create import get_text, get_image, get_dummy, get_col, get_row
from ....utils.web_template import Number, MultiNumber, StrWithArrow

NAME_2E = "2E"
rule2P = import_module("minesweepervariants.impl.rule.Rrule.2P")

class Rule2ESharp(AbstractClueSharp):
    name = ["2E#", "加密 + 标签", "Encrypted + Tag"]
    doc = ("线索被字母所取代，每个字母对应一个线索，且每个线索对应一个字母\n"
              "通过2E#:<rule1>;<rule2>;...来指定使用的规则及其顺序\n"
              "默认同二代\n"
              "可添加 1# 1#' 2# 2#''\n")
    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        self.rules = set()
        if not data:
            self.rules.update(["V", "2X", "2D", "2P", "2M", "2A"])
        else:
            rules = data.split(";")
            for rule in rules:
                if rule == "1#":
                    self.rules.update(["V", "1M", "1L", "1W", "1N", "1X", "1P", "1E"])
                elif rule == "1#'":
                    self.rules.update(["V", "1M", "1L", "1W", "1N", "1X", "1P", "1E", "1X'", "1K", "1W'", "1E'", "1L1M", "1M1N", "1M1X", "1N1X"])
                elif rule == "2#":
                    self.rules.update(["V", "2X", "2D", "2P", "2M", "2A"])
                elif rule == "2#'":
                    self.rules.update(["V", "2X", "2D", "2P", "2M", "2A", "2X'"])
                else:
                    self.rules.add(rule)
        super().__init__(list(self.rules), board)
        pos = board.boundary()
        size = min(pos.x + 1, 9)
        board.generate_board(NAME_2E, (size, size))
        board.set_config(NAME_2E, "pos_label", True)

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        self.init_clear(board)
        random = get_random()
        shuffled_nums = [i for i in range(min(9, board.boundary().x + 1))]
        random.shuffle(shuffled_nums)
        for x, y in enumerate(shuffled_nums):
            pos = board.get_pos(x, y, NAME_2E)
            board.set_value(pos, VALUE_CIRCLE)

        for pos, _ in board("N", key=NAME_2E):
            board.set_value(pos, VALUE_CROSS)
        boards : list[AbstractBoard] = []
        for rule in self.shape_rule.rules:
            boards.append(rule.fill(board.clone()))
        for pos, _ in board("N"):
            clues: list[AbstractClueValue] = [_board.get_value(pos) for _board in boards]
            select_queue = clues.copy()
            while len(select_queue) > 0:
                clue = random.choice(select_queue)
                select_queue.remove(clue)
                if clue is None:
                    continue
                type = clue.type().decode("ascii")
                if (type == '2A'):
                    flag = clue.flag
                    if flag == 4:
                        continue
                    value = clue.value
                    if value in shuffled_nums:
                        board.set_value(pos, Value2E2A(pos, value=shuffled_nums[value], flag=flag))
                    break
                elif (type == '2X'):
                    count = clue.count
                    value1 = shuffled_nums[count // 10]
                    value2 = shuffled_nums[count % 10]
                    board.set_value(pos, Value2E2X(pos, count=value1 * 10 + value2))
                    break
                elif (type == '2P'):
                    value_a, value_b = rule2P.sqrt_form(clue.value)
                    # A√B
                    if value_a in shuffled_nums and value_b in shuffled_nums:
                        board.set_value(pos, Value2E2P(pos, a=shuffled_nums[value_a], b=shuffled_nums[value_b]))
                        break
                    # A
                    elif value_a in shuffled_nums and value_b == -1:
                        if value_a in [1, 2]:
                            # 1/3 概率以 sqrt(A^2) 形式出现
                            if random.randint(0, 2) == 0:
                                board.set_value(pos, Value2E2P(pos, a=-1, b=shuffled_nums[value_a * value_a]))
                            else:
                                board.set_value(pos, Value2E2P(pos, a=shuffled_nums[value_a], b=-1))
                            break
                    # √B
                    elif value_b in shuffled_nums and value_a == -1:
                        board.set_value(pos, Value2E2P(pos, a=-1, b=shuffled_nums[value_b]))
                        break
                    continue
                elif (type == "1E'"):
                    value = clue.value
                    if value == 0:
                        board.set_value(pos, Value2E1EN(pos, value=shuffled_nums[0], arrow=random.randint(0, 1) == 1))
                        break
                    else:
                        board.set_value(pos, Value2E1EN(pos, value=shuffled_nums[abs(value)], arrow=value > 0))
                        break
                elif (type == '1W'):
                    # 跳过有多个数字的 1W 线索
                    if '.' in clue.__repr__():
                        continue

                value = int(clue.__repr__())
                if value in shuffled_nums:
                    board.set_value(pos, Value2ESharp(pos, value=shuffled_nums[value], rule=type))
                    break
            
            # 如果没有成功选择线索加密，就不加密随机选择一个线索
            if (board.get_type(pos) == "N"):
                board.set_value(pos, random.choice(clues))

        return board

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s_row = switch.get(model, self, '↔')
        s_col = switch.get(model, self, '↕')
        bound = board.boundary(key=NAME_2E)

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

    def init_clear(self, board: 'AbstractBoard'):
        for pos, _ in board(key=NAME_2E):
            board.set_value(pos, None)


class Value2ESharp(AbstractClueValue):
    def __init__(self, pos: AbstractPosition, value: int = 0, rule: str = '', code: bytes = None) -> None:
        super().__init__(pos)
        if code:
            self.value = code[0]
            self.rule = code[1:].decode("ascii", "ignore")
        else:
            self.value = value
            self.rule = rule

    def __str__(self) -> str:
        return "ABCDEFGHI"[self.value]

    def web_component(self, board) -> Dict:
        line = board.batch(board.get_col_pos(
            board.get_pos(0, self.value, NAME_2E)
        ), mode="type")
        if "F" in line:
            return Number(line.index("F"))
        return Number("ABCDEFGHI"[self.value])

    def compose(self, board) -> Dict:
        line = board.batch(board.get_col_pos(
            board.get_pos(0, self.value, NAME_2E)
        ), mode="type")
        if "F" in line:
            return get_col(
                get_dummy(height=0.3),
                get_text(str(line.index("F"))),
                get_dummy(height=0.3),
            )
        return get_col(
                get_dummy(height=0.3),
                get_text("ABCDEFGHI"[self.value]),
                get_dummy(height=0.3),
            )
    
    def high_light(self, board: 'AbstractBoard') -> List['AbstractPosition'] | None:
        return self.get_clue(1).high_light(board)

    @classmethod
    def type(cls) -> bytes:
        return Rule2ESharp.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value]) + self.rule.encode("ascii")
    
    def tag(self, board) -> bytes:
        return self.rule.encode("ascii")
    
    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        line = board.batch(board.get_col_pos(
            board.get_pos(0, self.value, NAME_2E)
        ), mode="variable")

        temp_list = []
        for index in range(len(line)):
            temp = model.NewBoolVar(f"temp_{self.pos}_{index}")
            model.Add(temp == 1).OnlyEnforceIf([line[index], s])
            self.get_clue(index).create_constraints(board, FakeSwitch(temp))
            temp_list.append(temp)
        model.Add(sum(temp_list) == 1).OnlyEnforceIf(s)

    def get_clue(self, value) -> AbstractClueValue:
        clue_code = bytearray()
        clue_code.extend(self.rule.encode("ascii"))
        clue_code.extend(b'|')
        clue_code.extend(bytes([value]))
        return get_value(self.pos, bytes(clue_code))
    
class Value2E2A(Value2ESharp):
    def __init__(self, pos: AbstractPosition, value: int = 0, code: bytes = None, flag = 4) -> None:
        super().__init__(pos, value, '2A', code)
        self.flag = flag

    @classmethod
    def type(cls):
        return "2E2A".encode("ascii")
    
    def get_clue(self, value) -> AbstractClueValue:
        clue_code = bytearray()
        clue_code.extend(self.rule.encode("ascii"))
        clue_code.extend(b'|')
        clue_code.extend(bytes([self.flag, value]))
        return get_value(self.pos, bytes(clue_code))

    
class Value2E2X(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', count: int = 0, code: bytes = None):
        super().__init__(pos, code)
        if code is not None:
            self.count = code[0]
        else:
            self.count = count
        self.neighbor = self.pos.neighbors(2)

    def __repr__(self) -> str:
        map = "ABCDEFGHI"
        return f"{map[self.count // 10]} {map[self.count % 10]}"
    
    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        return self.neighbor
    
    @classmethod
    def type(cls) -> bytes:
        return "2E2X".encode("ascii")

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
            board.get_pos(0, v, NAME_2E)
        ), mode="type") for v in values]
        texts = [(str(l.index("F")) if "F" in l else map[v]) for l, v in zip(lines, values)]
        texts.sort()
        return texts
    
    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        line_a = board.batch(board.get_col_pos(
            board.get_pos(0, self.count // 10, NAME_2E)
        ), mode="variable")
        line_b = board.batch(board.get_col_pos(
            board.get_pos(0, self.count % 10, NAME_2E)
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

class Value2E2P(AbstractClueValue):
    @staticmethod
    def convert_missing_value(x: int) -> int:
        if (x == -1):
            return 254
        elif (x == 254):
            return -1
        else:
            return x

    def __init__(self, pos: 'AbstractPosition', a: int = -1, b: int = -1, code: bytes = None):
        """
        A√B, -1 为缺失值
        """
        super().__init__(pos)
        if code:
            self.value_a = Value2E2P.convert_missing_value(code[0])
            self.value_b = Value2E2P.convert_missing_value(code[1])
        else:
            self.value_a = a
            self.value_b = b

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
        return "2E2P".encode("ascii")

    def code(self) -> bytes:
        return bytes([Value2E2P.convert_missing_value(self.value_a), Value2E2P.convert_missing_value(self.value_b)])

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
                board.get_pos(0, self.value_a, NAME_2E)
            ), mode="type")
            part_a = str(line_a.index("F")) if ("F" in line_a) else map[self.value_a]
        if self.value_b != -1:
            line_b = board.batch(board.get_col_pos(
                board.get_pos(0, self.value_b, NAME_2E)
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
    
    def create_constraints(self, board: 'AbstractBoard', switch):
        s = switch.get(board.get_model(), self)
        model = board.get_model()
        if self.value_a != -1 and self.value_b != -1:
            line_a = board.batch(board.get_col_pos(
                board.get_pos(0, self.value_a, NAME_2E)
            ), mode="variable")
            line_b = board.batch(board.get_col_pos(
                board.get_pos(0, self.value_b, NAME_2E)
            ), mode="variable")
            for i in range(len(line_a)):
                for j in range(len(line_b)):
                    temp_a = line_a[i]
                    temp_b = line_b[j]
                    temp_ab_combine = model.NewBoolVar(f"2E2P_temp_a_b_combine_{self.pos}_{i}_{j}")
                    model.AddBoolAnd([temp_a, temp_b, s]).OnlyEnforceIf(temp_ab_combine)
                    model.AddBoolOr([temp_a.Not(), temp_b.Not(), s.Not()]).OnlyEnforceIf(temp_ab_combine.Not())
                    self.create_2P(i * j * j).create_constraints(board, FakeSwitch(temp_ab_combine))
        elif self.value_a != -1:
            line_a = board.batch(board.get_col_pos(
                board.get_pos(0, self.value_a, NAME_2E)
            ), mode="variable")
            for i in range(len(line_a)):
                temp_a = line_a[i]
                clue_switch = model.NewBoolVar(f"2E2P_temp_clue_{self.pos}")
                model.AddBoolAnd([temp_a, s]).OnlyEnforceIf(clue_switch)
                model.AddBoolOr([temp_a.Not(), s.Not()]).OnlyEnforceIf(clue_switch.Not())
                self.create_2P(i * i).create_constraints(board, FakeSwitch(clue_switch))
        elif self.value_b != -1:
            line_b = board.batch(board.get_col_pos(
                board.get_pos(0, self.value_b, NAME_2E)
            ), mode="variable")
            for i in range(len(line_b)):
                temp_b = line_b[i]
                clue_switch = model.NewBoolVar(f"2E2P_temp_clue_{self.pos}")
                model.AddBoolAnd([temp_b, s]).OnlyEnforceIf(clue_switch)
                model.AddBoolOr([temp_b.Not(), s.Not()]).OnlyEnforceIf(clue_switch.Not())
                self.create_2P(i).create_constraints(board, FakeSwitch(clue_switch))

    def create_2P(self, value):
        if value > 254:
            return rule2P.Value2P(pos=self.pos, code=bytes([value // 255, value % 255]))
        return rule2P.Value2P(pos=self.pos, code=bytes([value]))
    
class Value2E1EN(AbstractClueValue):
    # arrow True 上下箭头，False 左右箭头
    def __init__(self, pos: 'AbstractPosition', value: int = 0, arrow: bool = True, code: bytes = None):
        super().__init__(pos)
        if code:
            self.value = code[0]
            self.arrow = code[1] == 1
        else:
            self.value = value
            self.arrow = arrow

    def __repr__(self):
        map = "ABCDEFGHI"
        if (self.arrow):
            return f"{map[self.value]}"
        else:
            return f"-{map[self.value]}"
        
    @classmethod
    def type(cls) -> bytes:
        return "2E1E'".encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value, 1 if self.arrow else 0])

    def tag(self, board) -> bytes:
        return "1E'".encode("ascii")
    
    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition'] | None:
        return self.create1EN(0).high_light(board)
    
    def web_component(self, board) -> Dict:
        line = board.batch(board.get_col_pos(
            board.get_pos(0, self.value, NAME_2E)
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
            board.get_pos(0, self.value, NAME_2E)
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
        
    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)

        line = board.batch(board.get_col_pos(
            board.get_pos(0, self.value, NAME_2E)
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
        return get_value(self.pos, bytes(clue_code))
        
    
class FakeSwitch(Switch):
    def __init__(self, var) -> None:
        self.var = var
        super().__init__()

    def get(self, model, obj, index=None):
        return self.var
