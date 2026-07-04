"""
[RL4] 最大四方雷数：线索表示所属的四个2x2区域内最大的总雷数
注：四个2x2区域是指以该格为公共角的四个区域，每个区域包含该格及相邻三个格
边界处只统计在棋盘内的格子
"""
from typing import List

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position


class RuleRL4(AbstractClueRule):
    id = "RL4"
    aliases = ()
    name = "Max Quadrant Mines"
    name.zh_CN = "最大四方雷数"
    doc = "Clue shows the maximum total mines among the four 2x2 areas containing the cell (only cells inside board are counted for edge areas)"
    doc.zh_CN = "线索表示所属的四个2x2区域内最大的总雷数（边界区域只统计在棋盘内的格子）"
    tags = ["Creative", "Local", "Number Clue", "Construction"]
    creation_time = "2026-07-04"
    author = ("雾", "3140864122")

    def fill(self, board: Board) -> Board:
        # 计算总雷数并存储到board，以便在约束中使用
        total_mines = sum(1 for pos, _ in board("always") if board.get_type(pos) == 'F')
        board._rl4_total_mines = total_mines
        
        for pos, _ in board("N"):
            grids = self._get_grids(pos)
            max_mines = 0
            for grid in grids:
                # 只统计在边界内的格子
                valid = [p for p in grid if board.in_bounds(p)]
                if valid:
                    mine_count = sum(1 for p in valid if board.get_type(p) == 'F')
                    if mine_count > max_mines:
                        max_mines = mine_count
            board.set_value(pos, ValueRL4(pos, bytes([max_mines])))
        return board

    @staticmethod
    def _get_grids(pos: Position) -> List[List[Position]]:
        return [
            [pos, pos.up(), pos.up().left(), pos.left()],
            [pos, pos.down(), pos.down().left(), pos.left()],
            [pos, pos.up(), pos.up().right(), pos.right()],
            [pos, pos.down(), pos.down().right(), pos.right()]
        ]

    @classmethod
    def clue_type(cls):
        return ValueRL4


class ValueRL4(AbstractClueValue):
    id = RuleRL4.id

    def __init__(self, pos: Position, code: bytes = b''):
        super().__init__(pos)
        self.value = code[0] if code else 0
        self.grids = RuleRL4._get_grids(pos)
        # 所有相关格子（去重）用于高亮
        self._highlight_positions = []
        seen = set()
        for grid in self.grids:
            for p in grid:
                if p not in seen:
                    seen.add(p)
                    self._highlight_positions.append(p)

    def __repr__(self) -> str:
        return str(self.value)

    def high_light(self, board: 'Board') -> List['Position']:
        return [p for p in self._highlight_positions if board.in_bounds(p)]

    @classmethod
    def type(cls) -> bytes:
        return RuleRL4.id.encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value])

    def create_constraints(self, board: 'Board', switch):
        # 对每个2x2区域，取在边界内的有效格子
        valid_grids = []
        for grid in self.grids:
            valid = [p for p in grid if board.in_bounds(p)]
            if valid:
                valid_grids.append(valid)
        
        model = board.get_model()
        s = switch.get(model, self)
        
        # 计算每个区域的总雷数变量（始终定义，不随s变化）
        region_sums = []
        for grid in valid_grids:
            vars_list = board.batch(grid, mode="variable")
            sum_var = model.NewIntVar(0, len(grid), f"sum_grid_{id(grid)}")
            model.Add(sum_var == sum(vars_list))
            region_sums.append(sum_var)

        if not region_sums:
            # 没有有效区域（不可能，至少包含自身），但为了安全
            model.Add(self.value == 0).OnlyEnforceIf(s)
            return

        # 最大值变量
        max_possible = max(len(g) for g in valid_grids)
        max_sum = model.NewIntVar(0, max_possible, "max_sum")
        model.AddMaxEquality(max_sum, region_sums)
        
        # 约束最大值等于线索值，仅在s为真时生效
        model.Add(max_sum == self.value).OnlyEnforceIf(s)
        
        # 增加总雷数约束，以增强求解确定性（适用于自动雷数模式）
        # 从board中获取已存储的总雷数（在fill中设置）
        if hasattr(board, '_rl4_total_mines'):
            total_mines = board._rl4_total_mines
            all_vars = board.batch(board.all_positions(), mode="variable")
            total = sum(all_vars)
            model.Add(total == total_mines)
