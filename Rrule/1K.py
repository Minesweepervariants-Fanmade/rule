"""
[1K]骑士:每个位置代表其马步位置格子的总雷值
"""

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition

from ....utils.tool import get_logger
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG


def encode_int_7bit(n: int) -> bytes:
    s = str(n)
    return s.encode()


def decode_bytes_7bit(data: bytes) -> int:
    s = data.decode()
    return int(s)

class RuleV(AbstractClueRule):
    name = ["1K", "K", "骑士", "Knight"]
    doc = "线索表示马步位置 8 个格子中的总雷值"

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        self.rule = data or "raw"

        class ValueV(AbstractClueValue):
            def __init__(self, pos: AbstractPosition, count: int = 0, code: bytes = None, rule=self.rule):
                super().__init__(pos, code)
                self.rule = rule
                if code is not None:
                    # 从字节码解码
                    self.count = decode_bytes_7bit(code)
                else:
                    # 直接初始化
                    self.count = count
                self.neighbor = self.pos.neighbors(5, 5)

            def __repr__(self):
                return f"{self.count}"

            @classmethod
            def type(cls) -> bytes:
                return self.rule.encode()

            def code(self) -> bytes:
                return encode_int_7bit(self.count)

            def create_constraints(self, board: 'AbstractBoard', switch):
                """创建CP-SAT约束: 周围雷数等于count"""
                model = board.get_model()

                # 收集周围格子的布尔变量
                neighbor_vars = []
                for neighbor in self.neighbor:  # 8方向相邻格子
                    if board.in_bounds(neighbor):
                        var = board.get_variable(neighbor, special=self.rule)
                        neighbor_vars.append(var)

                # 添加约束：周围雷数等于count
                if neighbor_vars:
                    model.Add(sum(neighbor_vars) == self.count).OnlyEnforceIf(switch.get(model, self.pos))

        self.ValueV = ValueV


    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        logger = get_logger()
        def val(s):
            if isinstance(s, str):
                return 1 if s == 'F' else 0
            return s

        for pos, _ in board("N", special='raw'):
            value = board.batch(pos.neighbors(5, 5), "type", special=self.rule)
            value = sum(val(v) for v in value)
            board.set_value(pos, self.ValueV(pos, count=value, rule=self.rule))
        return board

    def get_deps(self) -> list[str]:
        if self.rule == 'raw':
            return []
        return [self.rule]