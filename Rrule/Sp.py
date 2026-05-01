from minesweepervariants.impl.summon.solver import Switch

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition

class RuleSp(AbstractClueRule):
    id = "Sp"
    name = "Span"
    name.zh_CN = "跨越"
    doc = "线索表示能连接周围八格内所有雷的最短连续路径长度。"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        for pos, _ in board("N"):
            clue_value = ValueSp(pos, value=self._get_span_length(board, pos))
            board.set_value(pos, clue_value)
        return board

    def _get_span_length(self, board: AbstractBoard, pos: AbstractPosition) -> int:
        nei = [pos.right(), pos.right().down(), pos.down(), pos.left().down(),
               pos.left(), pos.left().up(), pos.up(), pos.right().up()]
        nei_var = [board.get_type(p) == 'F' for p in nei]
        nei_sum = sum(nei_var)
        if (nei_sum in [0, 1, 7, 8]):
            return nei_sum
        else:
            for n in range(2, 8):
                for i in range(8):
                    span_indexes = [(i + step) % 8 for step in range(n)]
                    if (sum(nei_var[j] for j in span_indexes) == nei_sum):
                        return n
        return -1

class ValueSp(AbstractClueValue):
    def __init__(self, pos: AbstractPosition, value: int = 0, code: bytes = None):
        super().__init__(pos, code)
        if code is not None:
            # 从字节码解码
            self.value = code[0]
        else:
            # 直接初始化
            self.value = value

    def __repr__(self):
        return f"{self.value}"

    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        return self.pos.neighbors(2)

    @classmethod
    def type(cls) -> bytes:
        return b'Sp'

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints(self, board: AbstractBoard, switch: Switch):
        pos = self.pos
        nei = [pos.right(), pos.right().down(), pos.down(), pos.left().down(),
               pos.left(), pos.left().up(), pos.up(), pos.right().up()]
        model = board.get_model()
        s = switch.get(model, self)
        if (self.value in [0, 1, 8]):
            model.Add(sum(board.batch(nei, mode="var", drop_none=True)) == self.value).OnlyEnforceIf(s)
        else:
            # 少于 value 的路径都不能涵盖所有雷
            for i in range(2, self.value):
                for start in range(8):
                    span_indexes = [(start + step) % 8 for step in range(i)]
                    model.Add(sum(board.batch([nei[j] for j in span_indexes], mode="var", drop_none=True)) < sum(board.batch(nei, mode="var", drop_none=True))).OnlyEnforceIf(s)
            # 至少存在一个长度为 value 的路径涵盖所有雷
            temp_vars = [model.NewBoolVar(f"{self.pos}_span_{start}") for start in range(8)]
            for start in range(8):
                span_indexes = [(start + step) % 8 for step in range(self.value)]
                model.Add(sum(board.batch([nei[j] for j in span_indexes], mode="var", drop_none=True)) == sum(board.batch(nei, mode="var", drop_none=True))).OnlyEnforceIf(temp_vars[start], s)
                model.Add(sum(board.batch([nei[j] for j in span_indexes], mode="var", drop_none=True)) != sum(board.batch(nei, mode="var", drop_none=True))).OnlyEnforceIf(temp_vars[start].Not(), s)
            model.AddBoolOr(temp_vars).OnlyEnforceIf(s)
