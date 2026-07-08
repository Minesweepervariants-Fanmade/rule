"""
[2P*] 距离差：线索表示距离该格最近的两个雷之间的曼哈顿距离差。
"""

from functools import lru_cache
from typing import List

from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position, JSONObject
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.position_set import PositionSet
from minesweepervariants.utils.tool import get_logger
from minesweepervariants.utils.value_template import SingleIntValue, is_value_template
from minesweepervariants.impl.summon.solver import Switch


@lru_cache(maxsize=None)
def manhattan_ring(pos: Position, distance: int) -> List[Position]:
    """
    返回距 pos 曼哈顿距离恰好为 distance 的所有位置（不进行边界裁剪）。
    """
    result = []
    if distance == 0:
        result.append(pos)
        return result
    for dx in range(distance + 1):
        dy = distance - dx
        if dx == 0:
            result.append(pos.up(dy))
            result.append(pos.down(dy))
        elif dy == 0:
            result.append(pos.left(dx))
            result.append(pos.right(dx))
        else:
            result.append(pos.up(dx).left(dy))
            result.append(pos.up(dx).right(dy))
            result.append(pos.down(dx).left(dy))
            result.append(pos.down(dx).right(dy))
    return result


@lru_cache(maxsize=None)
def manhattan_rings_range(pos: Position, from_dist: int, to_dist: int) -> List[Position]:
    """
    返回距 pos 曼哈顿距离在 [from_dist, to_dist] 范围内的所有位置。
    """
    result = []
    for d in range(from_dist, to_dist + 1):
        result.extend(manhattan_ring(pos, d))
    return result


class Rule2P(AbstractClueRule):
    id = "2P*"
    name = "Distance Difference"
    name.zh_CN = "距离差"  # type: ignore[attr-defined]
    doc = "Clue shows the difference of Manhattan distances to the nearest two mines"
    doc.zh_CN = "线索表示距离该格最近的两个雷之间的曼哈顿距离差"  # type: ignore[attr-defined]
    tags = ["Variant", "Local", "Number Clue", "Extensive Trial"]
    creation_time = "2026-03-01"
    author = ("咸鱼", 3898637422)

    def fill(self, board: Board) -> Board:
        """
        为所有未定义格子计算线索值：最近两个雷的曼哈顿距离差。
        """
        mine_positions = [pos for pos, _ in board("F")]
        if len(mine_positions) < 2:
            # 雷少于2个，所有非雷格子的值设为0（无意义）
            for pos, _ in board("N"):
                board.set_value(pos, Value2P(pos, diff=0))
            return board

        for pos, _ in board("N"):
            # 收集所有雷到 pos 的曼哈顿距离
            distances = []
            for mp in mine_positions:
                d = abs(mp.row - pos.row) + abs(mp.col - pos.col)
                distances.append(d)
            distances.sort()
            d1, d2 = distances[0], distances[1]
            diff = d2 - d1
            board.set_value(pos, Value2P(pos, diff=diff))
        return board


class Value2P(AbstractClueValue):
    id = Rule2P.id

    def __init__(self, pos: Position, diff: int):
        super().__init__(pos, b'')
        self.diff = diff
        self.value = SingleIntValue(diff)
        self.pos = pos

    def __repr__(self) -> str:
        return f"{self.diff}"

    @classmethod
    def from_json(cls, pos: Position, data: JSONObject) -> AbstractValue:
        _data = deep_unwrap(data)
        if not is_value_template(_data):
            raise TypeError(f"Expected value template, got {type(_data)}")
        value = SingleIntValue.try_from(_data)
        if value is None:
            raise ValueError("Invalid SingleIntValue data")
        return cls(pos, diff=value.value)

    def high_light(self, board: Board) -> List[Position]:
        """
        高亮显示所有可能影响该线索的格子：
        从距离1开始逐层向外，直到累计的（雷+未知）数量 >= 2。
        """
        n = 1
        total = 0
        highlighted = []
        while True:
            ring = manhattan_ring(self.pos, n)
            # 只保留在题板范围内的位置
            valid_ring = [p for p in ring if board.in_bounds(p)]
            if not valid_ring:
                break
            types = board.batch(valid_ring, mode="type")
            count_f_n = sum(1 for t in types if t in ("F", "N"))
            total += count_f_n
            for p, t in zip(valid_ring, types):
                if t in ("F", "N"):
                    highlighted.append(p)
            if total >= 2:
                break
            n += 1
        return highlighted

    def deduce_cells(self, board: Board) -> bool:
        """
        简单推理：如果最近两个雷的距离差为0，且某个距离上已经有至少2个雷，
        则更近的距离不能再有雷，更远的位置也不能有雷直到找到第二近的。
        这里保持保守，返回 False 表示不进行快速推理。
        """
        # 复杂推理留待后续优化，暂时不做快速推理
        return False

    def create_constraints(self, board: Board, switch: Switch) -> None:
        """
        为线索值构建 CP-SAT 约束。
        线索值 diff 表示最近两个雷的曼哈顿距离差。
        枚举所有可能的 (a, b) 组合，满足 a < b 且 b - a = diff，
        其中 a 是最近雷的距离，b 是第二近雷的距离。
        """
        model = board.get_model()
        logger = get_logger()
        s = switch.get(model, self)

        # 获取题板最大行列
        boundary_pos = board.boundary(self.pos.board_key)
        max_row = boundary_pos.row
        max_col = boundary_pos.col
        # 曼哈顿距离上界（保守）
        max_dist = max_row + max_col

        # 如果 diff == 0：最近两个雷在同一层 a 上
        if self.diff == 0:
            options = []
            for a in range(1, max_dist + 1):
                ring_a = manhattan_ring(self.pos, a)
                # 过滤出在题板内的位置
                valid_a = [p for p in ring_a if board.in_bounds(p)]
                if not valid_a:
                    continue
                var = model.NewBoolVar(f"2P*_diff0_{self.pos}_{a}")
                # 距离 a 处至少有 2 个雷
                vars_a = board.batch(valid_a, mode="variable", drop_none=True)
                if vars_a:
                    model.Add(sum(vars_a) >= 2).OnlyEnforceIf([var, s])
                else:
                    continue
                # 距离 < a 的位置没有雷
                inner = manhattan_rings_range(self.pos, 1, a - 1)
                valid_inner = [p for p in inner if board.in_bounds(p)]
                vars_inner = board.batch(valid_inner, mode="variable", drop_none=True)
                if vars_inner:
                    model.Add(sum(vars_inner) == 0).OnlyEnforceIf([var, s])
                options.append(var)
            if options:
                model.AddBoolOr(options).OnlyEnforceIf(s)
                logger.trace(f"[2P*] pos {self.pos} diff=0 added {len(options)} options")
            else:
                # 没有可行组合，禁用该线索
                model.Add(s == 0)
                logger.warning(f"[2P*] pos {self.pos} diff=0 no valid options, disabling")
            return

        # diff > 0: 枚举 a 和 b = a + diff
        options = []
        for a in range(1, max_dist + 1):
            b = a + self.diff
            if b > max_dist:
                break
            ring_a = manhattan_ring(self.pos, a)
            ring_b = manhattan_ring(self.pos, b)
            valid_a = [p for p in ring_a if board.in_bounds(p)]
            valid_b = [p for p in ring_b if board.in_bounds(p)]
            if not valid_a or not valid_b:
                continue

            var = model.NewBoolVar(f"2P*_{self.pos}_{a}_{b}")

            # 距离 a 处恰好有 1 个雷（最近的那个）
            vars_a = board.batch(valid_a, mode="variable", drop_none=True)
            if vars_a:
                model.Add(sum(vars_a) == 1).OnlyEnforceIf([var, s])
            else:
                continue

            # 距离 b 处至少有 1 个雷（第二近的那个）
            vars_b = board.batch(valid_b, mode="variable", drop_none=True)
            if vars_b:
                model.Add(sum(vars_b) >= 1).OnlyEnforceIf([var, s])
            else:
                continue

            # 距离 < a 的位置没有雷
            inner = manhattan_rings_range(self.pos, 1, a - 1)
            valid_inner = [p for p in inner if board.in_bounds(p)]
            vars_inner = board.batch(valid_inner, mode="variable", drop_none=True)
            if vars_inner:
                model.Add(sum(vars_inner) == 0).OnlyEnforceIf([var, s])

            # 距离在 (a, b) 之间的位置没有雷（即 a+1 到 b-1）
            middle = manhattan_rings_range(self.pos, a + 1, b - 1)
            valid_middle = [p for p in middle if board.in_bounds(p)]
            vars_middle = board.batch(valid_middle, mode="variable", drop_none=True)
            if vars_middle:
                model.Add(sum(vars_middle) == 0).OnlyEnforceIf([var, s])

            options.append(var)

        if options:
            model.AddBoolOr(options).OnlyEnforceIf(s)
            logger.trace(f"[2P*] pos {self.pos} diff={self.diff} added {len(options)} options")
        else:
            # 没有可行组合，禁用该线索
            model.Add(s == 0)
            logger.warning(f"[2P*] pos {self.pos} diff={self.diff} no valid options, disabling")
