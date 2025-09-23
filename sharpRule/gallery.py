from typing import Any, Generator, List, Tuple
from ortools.sat.python.cp_model import CpModel

from ....abs.Lrule import AbstractMinesRule
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition, MASTER_BOARD
from ....utils.impl_obj import VALUE_QUESS
from ....impl.impl_obj import get_rule
from ....impl.board.version3.board import Board
from ....impl.summon.solver import Switch
from minesweepervariants.utils.tool import get_random

predefined_left_rules = ['1Q', '1C', '1T', '1O', '1D', '1S', '1B', '1A']
predefined_right_rules = ['V', '1M', '1L', '1N', '1X', '1P', '1E', '1K']

all_left_rules = ['1Q', '1C', '1T', '1O', '1D', '1S', '1B', '1T\'', '1D\'', '1A', '2H', '2C', '2S', '2F', '2T', '2Z'] # 1H, 2G, 2B removed
all_right_rules = ['V', '1M', '1L', '1W', '1N', '1X', '1P', '1E', '1X\'', '1K', '1W\'', '1E\'', '2X', '2D', '2P', '2M', '2A', '2X\''] # 2E, 2L, 2I removed

class RuleGallery(AbstractClueRule):
    name = ["Gallery", "画廊", "Gallery"]
    doc = "每行每列的规则不同，在左上边界表明。左线规则只影响所在行及上下相邻的行。(1B 只有行平衡）在:后面添加参数，?表示随机顺序，!表示随机规则，这之后添加指定规则，规则间用;分隔，可只指定左线或右线规则。空的:相当于:!。"

    def __init__(self, board: "AbstractBoard" = None, data=None):
        super().__init__(board, data)
        if len(board.get_interactive_keys()) != 1:
            raise ValueError("目前一主板限定")
        x, y = board.get_config(MASTER_BOARD, 'size')
        if data is None:
            self.left_rules = predefined_left_rules[:x - 1]
            self.right_rules = predefined_right_rules[:y - 1]
        else:
            random = get_random()
            rand_rules = False
            rand_order = False
            if len(data) == 0:
                rand_rules = True
            elif len(data) > 1 and (data[:2] == "!?" or data[:2] == "?!" ):
                rand_order = True
                rand_rules = True
                data = data[2:]
            elif data[0] == "?":
                rand_order = True
                data = data[1:]
            elif data[0] == "!":
                rand_rules = True
                data = data[1:]
            if len(data) > 0:
                rules = data.split(";")
                self.left_rules = []
                self.right_rules = []
                for rule in rules:
                    rule_type = get_rule(rule)
                    if issubclass(rule_type, AbstractMinesRule):
                        self.left_rules.append(rule)
                    elif issubclass(rule_type, AbstractClueRule):
                        self.right_rules.append(rule)
                    else:
                        raise ValueError(f"不支持的规则 {rule}")
                if len(self.left_rules) == 0:
                    self.left_rules = random.sample(all_left_rules, x - 1) if rand_rules else predefined_left_rules[:x - 1]
                if len(self.right_rules) == 0:
                    self.right_rules = random.sample(all_right_rules, y - 1) if rand_rules else predefined_right_rules[:y - 1]
            else:
                self.left_rules = random.sample(all_left_rules, x - 1) if rand_rules else predefined_left_rules[:x - 1]
                self.right_rules = random.sample(all_right_rules, y - 1) if rand_rules else predefined_right_rules[:y - 1]
            if rand_order:
                random.shuffle(self.left_rules)
                random.shuffle(self.right_rules)
        if len(self.left_rules) != board.boundary().x or len(self.right_rules) != board.boundary().y:
            raise ValueError(f"Expected {board.boundary().x} left rules and {board.boundary().y} right rules, got {len(self.left_rules)} left rules and {len(self.right_rules)} right rules")
        
    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        boards : list[AbstractBoard] = []
        for rule in self.right_rules:
            boards.append(get_rule(rule)(board=board,data=None).fill(board.clone()))
        for pos, _ in board("N"):
            x, y = pos.x, pos.y
            if x == 0 or y == 0:
                continue
            board.set_value(pos, boards[y - 1].get_value(pos))
        return board
    
    def create_constraints(self, board: AbstractBoard, switch: Switch):
        model = board.get_model()
        origin_pos = board.get_pos(0, 0)
        model.Add(sum(board.batch(board.get_col_pos(origin_pos), mode="variable")) == 0)
        model.Add(sum(board.batch(board.get_row_pos(origin_pos), mode="variable")) == 0)
        y_size = board.get_config(MASTER_BOARD, 'size')[1]
        for i, rule in enumerate(self.left_rules):
            if i == 0:
                sub_board = SubBoard(board, board.get_pos(1, 1), board.get_pos(2, y_size - 1))
            elif i == len(self.left_rules) - 1:
                sub_board = SubBoard(board, board.get_pos(i, 1), board.get_pos(i + 1, y_size - 1))
            else:
                sub_board = SubBoard(board, board.get_pos(i, 1), board.get_pos(i + 2, y_size - 1))
            self.get_left_rule(rule, sub_board).create_constraints(board=sub_board, switch=FakeSwitch(switch.get(model, board.get_pos(i + 1, 0))))

    def init_board(self, board: AbstractBoard):
        board.set_value(board.get_pos(0, 0), VALUE_QUESS)
        for i, rule in enumerate(self.left_rules):
            pos = board.get_pos(i + 1, 0)
            board.set_value(pos, RuleRuleTag(pos, rule.encode("ascii")))
        for j, rule in enumerate(self.right_rules):
            pos = board.get_pos(0, j + 1)
            board.set_value(pos, RuleRuleTag(pos, rule.encode("ascii")))

    def get_left_rule(self, name, sub_board):
        if name == "1B" or name == "B":
            return Rule1B(board=sub_board, data=None)
        else:
            return get_rule(name)(board=sub_board, data=None)

    def suggest_total(self, info: dict):
        size = info["size"][MASTER_BOARD]
        info["soft_fn"]((size[0] - 1) * (size[1] - 1) * 0.4, 0)

class RuleRuleTag(AbstractClueValue):
    def __init__(self, pos: AbstractPosition, code: bytes):
        super().__init__(pos, code)
        self.value = code.decode("ascii")

    def __repr__(self):
        return self.value
    
    @classmethod
    def type(cls) -> bytes:
        return "".encode("ascii")
    
    def code(self) -> bytes:
        return self.value.encode("ascii")
    
class FakeSwitch(Switch):
    def __init__(self, var) -> None:
        self.var = var
        super().__init__()

    def get(self, model, obj, index=None):
        return self.var
    
class SubBoard(AbstractBoard):
    def __init__(self, parent: AbstractBoard, from_pos: AbstractPosition, to_pos: AbstractPosition) -> None:
        self.parent = parent
        self.from_pos = from_pos
        self.to_pos = to_pos
        self.size = (to_pos.x - from_pos.x + 1, to_pos.y - from_pos.y + 1)

    def __call__(self, target: str | None = "always", mode: str = "object", key: str | None = MASTER_BOARD, *args, **kwargs) -> Generator[Tuple[AbstractPosition, Any], Any, None]:
        for posx in range(self.size[0]):
            for posy in range(self.size[1]):
                pos = self.get_pos(posx, posy, key)
                pos_type = self.get_type(pos, special='raw')

                # 检查是否符合目标类型
                if target == "always" or pos_type in target:
                    if mode == "object":
                        yield pos, self.get_value(pos, *args, **kwargs)
                    elif mode == "obj":
                        yield pos, self.get_value(pos, *args, **kwargs)
                    elif mode == "type":
                        yield pos, self.get_type(pos, *args, **kwargs)
                    elif mode == "var":
                        yield pos, self.get_variable(pos, *args, **kwargs)
                    elif mode == "variable":
                        yield pos, self.get_variable(pos, *args, **kwargs)
                    elif mode == "dye":
                        yield pos, self.get_dyed(pos, *args, **kwargs)
                    elif mode == "none":
                        yield pos, None

    def get_board_keys(self) -> List[str]:
        return [MASTER_BOARD]

    def get_interactive_keys(self) -> List[str]:
        return [MASTER_BOARD]

    def get_real_pos(self, pos: AbstractPosition) -> AbstractPosition | None:
        return self.parent.get_pos(pos.x + self.from_pos.x, pos.y + self.from_pos.y) if self.in_bounds(pos) else None
    
    def get_model(self) -> CpModel:
        return self.parent.get_model()
    
    def get_variable(self, pos: AbstractPosition, special: str = ""):
        real_pos = self.get_real_pos(pos)
        return self.parent.get_variable(real_pos, special=special) if real_pos else None

    def get_type(self, pos: AbstractPosition, special: str = '') -> str:
        real_pos = self.get_real_pos(pos)
        return self.parent.get_type(real_pos, special=special) if real_pos else ''

    def get_value(self, pos: AbstractPosition):
        real_pos = self.get_real_pos(pos)
        return self.parent.get_value(real_pos) if real_pos else None

    def get_config(self, board_key: str, config_name: str):
        if config_name == 'size':
            return self.size
        else:
            return self.parent.get_config(board_key, config_name)
        
    def set_config(self, board_key: str, config_name: str, value: bool):
        return self.parent.set_config(board_key, config_name, value)
        
    def boundary(self, key=MASTER_BOARD) -> AbstractPosition:
        return self.get_pos(self.size[0] - 1, self.size[1] - 1, key)
    
    def get_dyed(self, pos: AbstractPosition) -> bool:
        real_pos = self.get_real_pos(pos)
        return self.parent.get_dyed(real_pos) if real_pos else False
    
    def batch(self, positions: List[AbstractPosition], mode: str, drop_none: bool = False, *args, **kwargs) -> List[Any]:
        result = []
        for pos in positions:
            if drop_none and not self.in_bounds(pos):
                continue
            if mode == "object":
                result.append(self.get_value(pos, *args, **kwargs))
            elif mode == "obj":
                result.append(self.get_value(pos, *args, **kwargs))
            elif mode == "variable":
                result.append(self.get_variable(pos, *args, **kwargs))
            elif mode == "var":
                result.append(self.get_variable(pos, *args, **kwargs))
            elif mode == "type":
                result.append(self.get_type(pos, *args, **kwargs))
            elif mode == "dye":
                result.append(self.get_dyed(pos, *args, **kwargs))
            else:
                raise ValueError(f"Unsupported mode: {mode}")
        return result
    
    def get_pos(self, x, y, key=MASTER_BOARD) -> AbstractPosition:
        return self.parent.get_pos(x, y, key)
    
    def get_row_pos(self, pos: AbstractPosition) -> List[AbstractPosition]:
        return [self.get_pos(x, pos.y) for x in range(0, self.boundary().x + 1)]
    
    def get_col_pos(self, pos: AbstractPosition) -> List[AbstractPosition]:
        return [self.get_pos(pos.x, y) for y in range(0, self.boundary().y + 1)]
    
    def get_pos_box(self, pos1: AbstractPosition, pos2: AbstractPosition) -> List[AbstractPosition]:
        return self.parent.get_pos_box(pos1, pos2)

    def generate_board(self, board_key: str, size: Tuple = ..., labels: List[str] = ..., code: bytes = None) -> None:
        raise NotImplementedError

    def encode(self) -> bytes:
        raise NotImplementedError

    @staticmethod
    def type_value(value) -> str:
        raise NotImplementedError

    def register_type_special(self, name: str, func):
        raise NotImplementedError

    def set_value(self, pos: AbstractPosition, value):
        raise NotImplementedError

    def clear_board(self):
        raise NotImplementedError

    def set_dyed(self, pos: AbstractPosition, dyed: bool):
        raise NotImplementedError

    def clear_variable(self):
        raise NotImplementedError

    def show_board(self, show_tag: bool = False):
        raise NotImplementedError

    def pos_label(self, pos: AbstractPosition) -> str:
        raise NotImplementedError
    
class Rule1B(AbstractMinesRule):
    name = ["1B-", "B-", "行平衡", "Row Balance"]
    doc = "每行雷数相等"

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s1 = switch.get(model, self)
        s2 = switch.get(model, self)
        for key in board.get_interactive_keys():
            boundary_pos = board.boundary(key=key)

            row_positions = board.get_row_pos(boundary_pos)
            row_sums = [
                sum(board.get_variable(_pos) for _pos in board.get_col_pos(pos))
                for pos in row_positions
            ]
            # 所有 row_sums 相等
            for i in range(1, len(row_sums)):
                model.Add(row_sums[i] == row_sums[0]).OnlyEnforceIf(s1)