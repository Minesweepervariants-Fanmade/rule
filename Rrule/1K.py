"""
[1K]骑士:每个位置代表其马步位置格子的总雷值
"""

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position

from ....utils.tool import get_logger
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG

BYTE_LENGTH = 3


def encode_int(num: int) -> bytes:
    """将整数编码为固定长度（BYTE_LENGTH）的字节串，不含 0xFF。小端序，高位补 0。"""
    if num < 0:
        raise ValueError("只支持非负整数")
    # 计算 255 进制表示（低位在前）
    digits = []
    temp = num
    while temp > 0:
        temp, r = divmod(temp, 255)
        digits.append(r)
    # 如果数字太大，超过固定长度则报错
    if len(digits) > BYTE_LENGTH:
        raise OverflowError(f"数字太大，需要至少 {len(digits)} 字节，当前 BYTE_LENGTH={BYTE_LENGTH}")
    # 补足到固定长度（末尾补 0，相当于高位补 0）
    digits += [0] * (BYTE_LENGTH - len(digits))
    return bytes(digits)[::-1]   # 每个元素 0~254，不会出现 255


def decode_int(data: bytes) -> int:
    """将固定长度的字节串解码为整数。data 长度必须等于 BYTE_LENGTH。"""
    if len(data) < BYTE_LENGTH:
        data = (BYTE_LENGTH - len(data)) * b'\x00' + data
    if len(data) > BYTE_LENGTH:
        raise ValueError(f"输入字节串长度必须为 {BYTE_LENGTH}，实际 {len(data)}")
    data = data[::-1]
    # 小端序：第 i 字节乘以 255^i
    num = 0
    for i, b in enumerate(data):
        if b > 254:
            raise ValueError(f"非法字节值 {b}（最大应为 254）")
        num += b * (255 ** i)
    return num


class RuleV(AbstractClueRule):
    id = "1K"
    aliases = ("K",)
    name = "Knight"
    name.zh_CN = "骑士"
    doc = "Clue indicates the total mine value at the eight knight's move positions"
    doc.zh_CN = "线索表示马步位置 8 个格子中的总雷值"
    tags = ["Original", "Local", "Number Clue"]
    creation_time = "2025-08-06"
    author = ("", 0)

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        self.rule = data or "raw"

        class ValueV(AbstractClueValue):
            id = "V"
            def __init__(self, pos: Position, count: int = 0, code: bytes = None, rule=self.rule):
                super().__init__(pos, code)
                self.rule = rule
                if code is not None:
                    # 从字节码解码
                    self.count = decode_int(code)
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
                return encode_int(self.count)

            def create_constraints(self, board: 'Board', switch):
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


    def fill(self, board: 'Board') -> 'Board':
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