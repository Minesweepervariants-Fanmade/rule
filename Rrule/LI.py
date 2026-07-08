# -*- coding: utf-8 -*-
"""
[LI] 连线 (Line): 线索表示将任意两雷连线，经过该格的线的数量，包含边界和四角
"""
from typing import Optional, List, Tuple, Dict
from ortools.sat.python import cp_model

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board
from minesweepervariants.position import Position
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.utils.tool import get_logger
from minesweepervariants.utils.value_template import SingleIntValue

logger = get_logger(__name__)


class RuleLI(AbstractClueRule):
    """连线规则：线索表示将任意两雷连线，经过该格的线的数量"""

    id = "LI"
    name = "Line"
    name.zh_CN = "连线"
    doc = "Clue shows the number of lines connecting any two mines that pass through this cell, including boundaries and corners"
    doc.zh_CN = "线索表示将任意两雷连线，经过该格的线的数量，包含边界和四角"
    author = ("小绿草", 3021857082)
    tags = ["Original", "Local", "Number Clue"]
    creation_time = "2026-05-25 20:40:27"

    def __init__(self, board: Optional[Board] = None, data: Optional[dict] = None):
        super().__init__(board=board, data=data)

    @staticmethod
    def segment_through(p1: Position, p2: Position, p: Position) -> bool:
        """
        判断线段 p1-p2 是否经过格子 p（包括边界和四角）。
        使用参数区间交集法，精确处理浮点边界。
        格子 p 的中心在 (p.row, p.col)，矩形区域为 [row-0.5, row+0.5] × [col-0.5, col+0.5]
        """
        # 坐标转换为浮点数
        x1, y1 = float(p1.row), float(p1.col)
        x2, y2 = float(p2.row), float(p2.col)
        left = p.row - 0.5
        right = p.row + 0.5
        bottom = p.col - 0.5
        top = p.col + 0.5

        # 如果端点之一在矩形内（包括边界），则线段经过矩形
        if (left <= x1 <= right and bottom <= y1 <= top) or \
           (left <= x2 <= right and bottom <= y2 <= top):
            return True

        # 参数 t 的范围 [0,1]
        t_low = 0.0
        t_high = 1.0

        dx = x2 - x1
        dy = y2 - y1

        # 对于 x 方向，求 t 的范围使得 x1 + t*dx 在 [left, right]
        if abs(dx) < 1e-12:
            # 线段垂直，检查 x1 是否在区间内
            if x1 < left or x1 > right:
                return False
        else:
            t1 = (left - x1) / dx
            t2 = (right - x1) / dx
            low = min(t1, t2)
            high = max(t1, t2)
            t_low = max(t_low, low)
            t_high = min(t_high, high)
            if t_low > t_high + 1e-12:
                return False

        # 对于 y 方向，求 t 的范围使得 y1 + t*dy 在 [bottom, top]
        if abs(dy) < 1e-12:
            if y1 < bottom or y1 > top:
                return False
        else:
            t1 = (bottom - y1) / dy
            t2 = (top - y1) / dy
            low = min(t1, t2)
            high = max(t1, t2)
            t_low = max(t_low, low)
            t_high = min(t_high, high)
            if t_low > t_high + 1e-12:
                return False

        # 如果交集非空，则线段经过矩形
        return True

    def fill(self, board: Board) -> Board:
        """
        根据当前的雷布局，为每个未定义格计算线索值：
        统计所有雷对连线经过该格子的数量。
        """
        # 获取所有雷的位置
        mines = [pos for pos, _ in board() if board.get_type(pos) == 'F']
        if len(mines) < 2:
            # 少于2个雷，所有线索值为0
            for pos, _ in board():
                if board.get_type(pos) == 'N':
                    board.set_value(pos, ValueLI(pos, 0))
            return board

        # 获取所有未定义格
        unknown_positions = [pos for pos, _ in board() if board.get_type(pos) == 'N']

        # 为每个未定义格统计经过的雷对数量
        for pos in unknown_positions:
            count = 0
            for i in range(len(mines)):
                for j in range(i + 1, len(mines)):
                    if self.segment_through(mines[i], mines[j], pos):
                        count += 1
            board.set_value(pos, ValueLI(pos, count))

        return board

    def suggest_total(self, info: dict) -> tuple[int, int, bool] | None:
        """
        向生成器建议总雷数范围。
        对于连线规则，需要至少2个雷才有连线，且密度不宜过高以免约束过强。
        建议密度在 10% ~ 30% 之间。
        """
        total_cells = 0
        for key in info.get("interactive", []):
            total_cells += info.get("total", {}).get(key, 0)

        if total_cells == 0:
            return None

        min_mines = max(2, int(total_cells * 0.1))
        max_mines = min(total_cells - 1, int(total_cells * 0.3))
        if min_mines < 2:
            min_mines = 2
        if max_mines < 2:
            max_mines = 2
        return (min_mines, max_mines, False)


class ValueLI(AbstractClueValue):
    """
    线索值对象，存储 [LI] 规则中每个格子的数字线索。
    """
    id = "LI"

    def __init__(self, pos: Position, value: int):
        super().__init__(pos)
        self.value = SingleIntValue(value)

    def code(self):
        return (self.value.value,)

    @classmethod
    def from_json(cls, pos: Position, data):
        """
        从 JSON 数据重建 ValueLI 对象。
        使用 SingleIntValue.try_from 解析数据，兼容多种格式。
        """
        from minesweepervariants.utils.value_template import SingleIntValue
        from minesweepervariants.json_object import deep_unwrap
        
        # 解包数据
        _data = deep_unwrap(data)
        
        # 尝试用 SingleIntValue 解析
        value = SingleIntValue.try_from(_data)
        if value is not None:
            return cls(pos, value.value)
        
        # 如果解析失败，尝试从 code 字段提取
        if isinstance(_data, dict) and "code" in _data:
            val = _data["code"]
            if isinstance(val, (list, tuple)) and len(val) > 0:
                return cls(pos, int(val[0]))
        
        raise ValueError(f"Invalid JSON for ValueLI: {data}")

    # 不需要重写 json，使用父类的默认实现，它会调用 code()

    def create_constraints(self, board: Board, switch: Switch):
        """
        为当前线索添加 CP-SAT 约束：
        经过该格子的所有雷对数量等于其线索值。
        """
        model = board.get_model()
        s = switch.get(model, self.pos)

        # 获取所有雷的位置
        mines = [pos for pos, _ in board() if board.get_type(pos) == 'F']
        if len(mines) < 2:
            # 没有雷对，约束值必须为 0
            model.Add(self.value.value == 0).OnlyEnforceIf(s)
            return

        # 获取所有位置的变量
        pos_vars = {pos: board.get_variable(pos) for pos, _ in board()}

        # 收集经过当前格子的雷对
        pairs = []
        for i in range(len(mines)):
            for j in range(i + 1, len(mines)):
                if RuleLI.segment_through(mines[i], mines[j], self.pos):
                    pairs.append((mines[i], mines[j]))

        if not pairs:
            model.Add(self.value.value == 0).OnlyEnforceIf(s)
            return

        # 创建辅助变量并求和
        # 使用 board 缓存辅助变量以避免重复创建（跨线索共享）
        if not hasattr(board, '_li_pair_cache'):
            board._li_pair_cache = {}
        cache = board._li_pair_cache

        vars_to_sum = []
        for (p1, p2) in pairs:
            # 排序确保键一致
            key = (p1, p2) if (p1.row, p1.col) <= (p2.row, p2.col) else (p2, p1)
            if key not in cache:
                y = model.NewBoolVar(f"pair_{key[0].row}_{key[0].col}_{key[1].row}_{key[1].col}")
                x1 = pos_vars[key[0]]
                x2 = pos_vars[key[1]]
                model.AddMultiplicationEquality(y, [x1, x2])
                cache[key] = y
            vars_to_sum.append(cache[key])

        if vars_to_sum:
            model.Add(sum(vars_to_sum) == self.value.value).OnlyEnforceIf(s)
        else:
            model.Add(self.value.value == 0).OnlyEnforceIf(s)

    def __repr__(self):
        return str(self.value.value)

    def compose(self, board):
        return self.value.compose()

    def web_component(self, board):
        return self.value.web_component()
