from ortools.sat.python.cp_model import CpModel, IntVar
from typing import Any, Generator, List

from ....abs.board import MASTER_BOARD, AbstractPosition

from ....abs.Rrule import AbstractClueRule
from ....impl.rule.Rrule.V import RuleV
from ....abs.board import AbstractBoard
from ..Rrule.sharp import RuleSharp as ClueSharp
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG

class RuleDJ(AbstractClueRule):
    name = ["DJ", "不相交", "Disjoint"]
    doc = "存在两个主板，两个主板同一位置的格子不能都是雷。DJ:A+B;C+D 表示左板为 A B 规则，右板为 C D 规则"

    def __init__(self, board: AbstractBoard = None, data: str = 'V;V') -> None:
        super().__init__(board, data)
        size = (board.boundary().x + 1, board.boundary().y + 1)
        board.generate_board('2', size)
        board.set_config('2', "interactive", True)
        board.set_config('2', "row_col", True)
        board.set_config('2', "VALUE", VALUE_QUESS)
        board.set_config('2', "MINES", MINES_TAG)
        left_data, right_data = data.split(";")
        left_data = left_data.split("+")
        right_data = right_data.split("+")
        self.left_rules = []
        temp_board = board.clone()
        for data in left_data:
            if (':' in data):
                self.left_rules.append(board.get_rule_instance(data.split(":")[0], data.split(":")[1], add=False))
            else:
                self.left_rules.append(board.get_rule_instance(data, add=False))
        self.right_rules = []
        for data in right_data:
            if (':' in data):
                self.right_rules.append(board.get_rule_instance(data.split(":")[0], data.split(":")[1], add=False))
            else:
                self.right_rules.append(board.get_rule_instance(data, add=False))
        self.left_rule = ClueSharp(board=board, data=[rule for rule in self.left_rules if isinstance(rule, AbstractClueRule)])
        self.right_rule = ClueSharp(board=board, data=[rule for rule in self.right_rules if isinstance(rule, AbstractClueRule)])
        if not self.left_rule.rules:
            self.left_rule = RuleV()
        if not self.right_rule.rules:
            self.right_rule = RuleV()
        board.set_config('1', "by_mini", sum(1 for rule in self.left_rules if isinstance(rule, AbstractClueRule)) > 1)
        board.set_config('2', "by_mini", sum(1 for rule in self.right_rules if isinstance(rule, AbstractClueRule)) > 1)
        

    def fill(self, board: AbstractBoard) -> AbstractBoard:
        _board = board.clone()
        self.left_rule.fill(_board)
        for pos, _ in board('N', key='1'):
            board.set_value(pos, _board.get_value(pos))
        _board = board.clone()
        self.right_rule.fill(_board)
        for pos, _ in board('N', key='2'):
            board.set_value(pos, _board.get_value(pos))
        return board

    def create_constraints(self, board: 'AbstractBoard', switch):
        sub_board_1 = SubBoard(board, '1')
        sub_board_2 = SubBoard(board, '2')
        for pos, _ in board(key='1'):
            var1 = sub_board_1.get_variable(pos)
            var2 = sub_board_2.get_variable(pos)
            board.get_model().Add(var1 + var2 <= 1)
        for rule in self.left_rules:
            rule.create_constraints(sub_board_1, switch)
        for rule in self.right_rules:
            rule.create_constraints(sub_board_2, switch)
    
class SubBoard(AbstractBoard):
    def __init__(self, board: AbstractBoard, key: str):
        self.board = board
        self.key = key

    def __call__(self, target: str | None = "always", mode: str = "object", key: str | None = '1', *args, **kwargs) -> Generator[tuple[AbstractPosition, Any], Any, None]:
        for pos, value in self.board(target=target, mode=mode, key=self.key, *args, **kwargs):
            yield pos, value

    def get_value(self, pos):
        _pos = pos.clone()
        _pos.board_key = self.key
        return self.board.get_value(_pos)
    
    def set_value(self, pos, value):
        _pos = pos.clone()
        _pos.board_key = self.key
        self.board.set_value(_pos, value)

    def get_variable(self, pos: AbstractPosition, special: str = '') -> IntVar:
        _pos = pos.clone()
        _pos.board_key = self.key
        return self.board.get_variable(_pos, special)
    
    def get_board_keys(self) -> list[str]:
        return ['1']
    
    def get_interactive_keys(self) -> list[str]:
        return ['1']
    
    def get_config(self, key: str, name: str):
        return self.board.get_config(self.key, name)
    
    def set_config(self, key: str, name: str, value):
        self.board.set_config(self.key, name, value)

    def get_rule_instance(self, name: str, data=None):
        return self.board.get_rule_instance(name, data)
    
    def get_model(self) -> CpModel:
        return self.board.get_model()
    
    def get_pos(self, x, y, key='1') -> AbstractPosition:
        return self.board.get_pos(x, y, key)
    
    def get_pos_box(self, pos1: AbstractPosition, pos2: AbstractPosition) -> List[AbstractPosition]:
        return self.board.get_pos_box(pos1, pos2)
    
    def get_col_pos(self, pos: AbstractPosition) -> List[AbstractPosition]:
        return self.board.get_col_pos(pos)
    
    def get_row_pos(self, pos: AbstractPosition) -> List[AbstractPosition]:
        return self.board.get_row_pos(pos)
    
    def get_dyed(self, pos: AbstractPosition) -> bool:
        return self.board.get_dyed(pos)
    
    def get_type(self, pos: AbstractPosition) -> str:
        return self.board.get_type(pos)
    
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
    
    def boundary(self, key='1') -> AbstractPosition:
        return self.board.boundary(key=self.key)

    def generate_board(self, board_key: str, size: tuple = (), labels: List[str] = [], code: bytes = None) -> None:
        raise NotImplementedError

    def encode(self) -> bytes:
        raise NotImplementedError

    @staticmethod
    def type_value(value) -> str:
        raise NotImplementedError

    def register_type_special(self, name: str, func):
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

    


    