"""
[1ES] 螺旋视野 (Spiral Eyesight)：该线索表示从当前格子向四周出发，随后进行顺时针顺序旋转（类似卐字形），统计在遇到雷前能看到的非雷格数量（包含自身）。
"""
from .eyesight import AbstractEyesightClueRule, AbstractEyesightClueValue


class Rule1EQ(AbstractEyesightClueRule):
    name = ["1ES", "螺旋视野", "Spiral Eyesight"]
    doc = "该线索表示从当前格子向四周出发随后进行顺时针顺序旋转（类似卐字形）能看到的非雷格数量（包含自身）, 雷会阻挡视线。"

    @staticmethod
    def direction_funcs(pos):
        def move_wan(_pos, value, k=0):
            a = int(value ** 0.5 + 0.5)
            dy = None
            dx = None

            if (a + k) % 2 == 0:
                dx = a
            else:
                dy = a
            if (a + k + 1) // 2 % 2 == 1:
                if dx is None:
                    dy = -dy
                else:
                    dx = -dx
            
            dxy = value - a ** 2
            if dx is None:
                dx = dxy if dy > 0 else -dxy
            else:
                dy = -dxy if dx > 0 else dxy

            return _pos.shift(dy, dx)
        return [
            lambda n:move_wan(pos.clone(), n, 0),
            lambda n:move_wan(pos.clone(), n, 1),
            lambda n:move_wan(pos.clone(), n, 2),
            lambda n:move_wan(pos.clone(), n, 3),
        ]
    
    @classmethod
    def clue_type(cls):
        return Value1EQ

class Value1EQ(AbstractEyesightClueValue):
    def direction_funcs(self):
        return Rule1EQ.direction_funcs(self.pos)
    
    @classmethod
    def type(cls) -> bytes:
        return Rule1EQ.name[0].encode("ascii")
