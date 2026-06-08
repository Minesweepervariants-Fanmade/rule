'''
RF Rule Split Definition

1. 规则对象与适用范围:
   - 适用于非雷格（线索格），对每个线索格计算其线索值。
   - 全局约束：每个线索格的值必须满足下述计数规则。

2. 核心术语定义:
   - “相反方向”：指从线索格到相邻雷格的方向的相反方向。
   - “视线”：沿相反方向的直线，直到遇到雷格或棋盘边缘为止。
   - “雷会遮挡视线”：若在视线路径上出现雷格，则视线在该雷格处终止，不计入该格。

3. 计数对象、边界条件、越界处理:
   - 计数对象为视线路径上所有非雷格（**包括线索格本身**）。
   - 当视线到达棋盘边缘时，视线在边缘外结束。
   - 若视线在途中遇到雷格，则该雷格不计入，视线在其前一格结束。

4. fill 与 create_constraints 等价关系:
   - fill 阶段：遍历八个相邻格，若相邻格为雷，则沿其相反方向遍历，统计可见的非雷格数量，得到 count。
   - create_constraints 阶段：为每个线索格生成约束，使其 count 等于上述统计结果。

5. 可验证样例:
   ```
   ???FF
   FF?FF
   ?????
   F?F??
   ?F?F?
   ```
   中心格的线索值应为 7，因为在相反方向可见的格子数为 7（示意图中 X 为不可计入，O 为计入）。
   例如, 对于雷分布, 其中?表示非雷格, F表示雷格
   ```
   XXOFF
   FFOFF
   XXOXX
   FOFOX
   OFXFO
   ```
'''

from typing import Dict
from ortools.sat.python.cp_model import CpModel
from minesweepervariants.abs.Rrule import AbstractClueValue, AbstractClueRule
from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue
from minesweepervariants.board import JSONObject, Position, Board
def opposite_move(p: Position, dx: int, dy: int) -> Position:
    # 根据相对位移 (dx, dy) 选择相反方向的移动
    if dx == -1 and dy == 0:   # 上方有雷 → 向下
        return p.down()
    if dx == 1 and dy == 0:    # 下方有雷 → 向上
        return p.up()
    if dx == 0 and dy == -1:   # 左方有雷 → 向右
        return p.right()
    if dx == 0 and dy == 1:    # 右方有雷 → 向左
        return p.left()
    if dx == -1 and dy == -1:  # 左上有雷 → 向右下
        return p.down().right()
    if dx == -1 and dy == 1:   # 右上有雷 → 向左下
        return p.down().left()
    if dx == 1 and dy == -1:   # 左下有雷 → 向右上
        return p.up().right()
    if dx == 1 and dy == 1:    # 右下有雷 → 向左上
        return p.up().left()
    # 不应到达此处
    raise ValueError(f"Invalid relative position: dx={dx}, dy={dy}")


class RuleRF(AbstractClueRule):
    id = "RF"
    name = "Reflect"
    name.zh_CN = "反射"
    doc = "Clue indicates the number of visible cells in the opposite direction of each adjacent mine; mines block sight."
    doc.zh_CN = "线索表示周围八格中，有雷的方向相反的方向可以看到的格数。雷会遮挡视线。"
    tags = ["Creative", "Local", "Number Clue"]
    creation_time = "2026-04-29"
    author = ("NT", 2201963934)

    def fill(self, board: 'Board') -> 'Board':

        for pos, _ in board("N"):
            count = 0
            has_mine = False
            # 获取所有相邻格（距离 1）
            for neighbor in pos.neighbors(2):
                if board.get_type(neighbor) != "F":
                    continue
                has_mine = True
                # 计算相对位移
                dx = neighbor.row - pos.row
                dy = neighbor.col - pos.col
                cur = pos.clone()
                step = 0
                while True:
                    cur = opposite_move(cur, dx, dy)
                    step += 1
                    if not board.in_bounds(cur):
                        break
                    if board.get_type(cur) == "F":
                        break
                    # 可见的非雷格计数（不含线索格本身）
                    count += 1
            # 有雷时才加1，无雷时为0
            if has_mine:
                count += 1
            board.set_value(pos, ValueRF(pos, count=count))
        return board



class ValueRF(AbstractClueValue):
    id = RuleRF.id
    """RF 规则对应的线索值对象。

    ``count`` 为在 ``fill`` 阶段统计得到的可见非雷格数量。
    ``code`` 使用单字节表示该整数，以便在保存/加载时保持兼容。
    """

    def __init__(self, pos: 'Position', count: int = 0, code: bytes = None):
        # 兼容已有的 ``code`` 读取方式
        super().__init__(pos, code)
        if code is not None:
            self.count = code[0]
        else:
            self.count = count

    def __repr__(self) -> str:
        return str(self.count)

    @classmethod
    def type(cls) -> bytes:
        return RuleRF.id.encode("ascii")

    def code(self) -> bytes:
        return bytes([self.count])

    def high_light(self, board: 'Board') -> list['Position']:
        """Return positions that contribute to the clue value.

        The clue counts the number of visible non‑mine cells in the opposite
        direction of each adjacent mine (plus a flag when any mine exists). For
        visualisation we highlight the clue cell itself and all cells that are
        counted as visible.
        """
        positions: list['Position'] = [self.pos]
        # Iterate over the eight neighboring positions.
        for neighbor in self.pos.neighbors(2):
            if board.get_type(neighbor) == "N":
                positions.append(neighbor)
                continue
            elif board.get_type(neighbor) != "F":
                continue
            # Direction from the clue to the mine.
            dx = neighbor.row - self.pos.row
            dy = neighbor.col - self.pos.col
            # Walk in the opposite direction, adding cells until a mine or the
            # board edge is encountered.
            cur = opposite_move(self.pos, dx, dy)
            while board.in_bounds(cur) and board.get_type(cur) != "F":
                positions.append(cur)
                cur = opposite_move(cur, dx, dy)
        return positions

    def create_constraints(self, board: 'Board', switch):
        # Build CP-SAT constraints that enforce the clue value computed in ``fill``.
        # The clue counts the number of visible non‑mine cells in the opposite
        # direction of each adjacent mine, plus 1 if there is at least one adjacent
        # mine. Visibility stops when a mine is encountered or the board edge is
        # reached.
        model = board.get_model()
        s = switch.get(model, self)

        pos = self.pos
        # List to collect all Bool vars that represent counted visible cells.
        visible_vars: list = []
        # Bool vars for each adjacent position indicating whether it is a mine.
        adjacent_mine_vars: list = []

        for neighbor in pos.neighbors(2):
            dx = neighbor.row - pos.row
            dy = neighbor.col - pos.col
            mine_var = board.get_variable(neighbor)
            if mine_var is None:
                continue
            adjacent_mine_vars.append(mine_var)

            # Only when this neighbor is a mine do we start counting visible cells.
            cur = opposite_move(pos, dx, dy)
            prev_cont = None
            step = 0
            while board.in_bounds(cur):
                cont = model.NewBoolVar(f"rf_cont_{pos}_{dx}_{dy}_{step}")
                # First cell in the line: visible iff neighbor is a mine and the cell is not a mine.
                if prev_cont is None:
                    model.Add(cont == 1).OnlyEnforceIf([mine_var, board.get_variable(cur).Not(), s])
                    model.Add(cont == 0).OnlyEnforceIf([board.get_variable(cur), s])
                    # If the neighbor is not a mine, force cont to 0.
                    model.Add(cont == 0).OnlyEnforceIf(mine_var.Not(), s)
                else:
                    # Continuation: visible only if previous cell was visible and this cell is not a mine.
                    model.Add(cont == 1).OnlyEnforceIf([prev_cont, board.get_variable(cur).Not(), s])
                    model.Add(cont == 0).OnlyEnforceIf([prev_cont.Not(), s])
                    model.Add(cont == 0).OnlyEnforceIf(board.get_variable(cur), s)
                visible_vars.append(cont)
                prev_cont = cont
                cur = opposite_move(cur, dx, dy)
                step += 1

        # Flag indicating whether at least one adjacent mine exists.
        any_mine = model.NewBoolVar(f"rf_any_mine_{pos}")
        if adjacent_mine_vars:
            model.AddBoolOr(adjacent_mine_vars).OnlyEnforceIf(any_mine)
            model.AddBoolAnd([v.Not() for v in adjacent_mine_vars]).OnlyEnforceIf(any_mine.Not())
        else:
            model.Add(any_mine == 0)

        # The clue value equals the number of counted visible cells plus the any‑mine flag.
        model.Add(sum(visible_vars) + any_mine == self.count).OnlyEnforceIf(s)