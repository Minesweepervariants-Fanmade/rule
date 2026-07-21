"""
[2M''∞] 无穷多雷：每行每列恰好有一个雷值为∞
"""
from typing import Self
from ortools.sat.python.cp_model import CpModel

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.utils.tool import get_logger
from minesweepervariants.utils.value_template import Template, SingleValue

NAME_2Minf = "2M''inf"


class Rule2M_inf(AbstractClueRule):
    id = "2M''inf"
    aliases = ("2M''∞", )
    name = "Infinite Mines"
    name.zh_CN = "无穷多雷"
    doc = "Exactly one mine with value ∞ per row and per column"
    doc.zh_CN = "每行每列恰好有一个雷值为∞"
    tags = ["Variant", "Global", "Mine-Counting"]
    creation_time = "2026-07-17"
    lib_only = False
    author = ("NT", 2201963934)

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        """
        为每行每列添加恰好一个雷的约束。
        """
        model: CpModel = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            for pos, var in board(mode="var"):
                var_inf = model.new_bool_var(f"{pos}_inf")
                model.add_bool_and(var).only_enforce_if(var_inf)
                board.register_variable_special(NAME_2Minf, pos, var_inf)
            pos_bound = board.boundary(key)
            pos_bound_col = board.get_col_pos(pos_bound)
            pos_bound_row = board.get_row_pos(pos_bound)

            for pos_col in pos_bound_col:
                each_row = board.get_row_pos(pos_col)
                each_row_var = board.batch(each_row, mode="var", special=NAME_2Minf)
                model.add(sum(each_row_var) == 1).only_enforce_if(s)

            for pos_row in pos_bound_row:
                each_col = board.get_col_pos(pos_row)
                each_col_var = board.batch(each_col, mode="var", special=NAME_2Minf)
                model.add(sum(each_col_var) == 1).only_enforce_if(s)

    def fill(self, board: 'Board') -> 'Board':
        from minesweepervariants.impl.summon.solver import solver_model
        from ortools.sat.python.cp_model import INFEASIBLE, CpSolver
        logger = get_logger()
        model = board.get_model().clone()
        for _, var in board("N", mode="var"):
            model.add(var == 0)
        status, solver = solver_model(model, True)
        solver: CpSolver
        if not status:
            logger.warning("题板无解? 为什么你能走到这")
            logger.warning("\n" + str(board))
            raise ValueError("题板无解")    # 为什么无解?我不知道
        for pos, _ in board("N"):
            pos_nei = [_pos for _pos in pos.neighbors(2) if board.is_valid(_pos)]
            pos_nei_var = board.batch(pos_nei, mode="var", special=NAME_2Minf)
            if 1 in [solver.value(var) for var in pos_nei_var]:
                obj = Value2M_inf(pos, -1)
            else:
                obj = Value2M_inf(pos, board.batch(pos_nei, mode="type").count("F"))
            board[pos] = obj
        return board


class Value2M_inf(AbstractClueValue):
    id = Rule2M_inf.id

    def __init__(self, pos: 'Position', value: int, *args: object, **kwargs: object):
        super().__init__(pos, *args, **kwargs)
        self.value: SingleValue = SingleValue(value)
        self.count = value

    @classmethod
    def from_json(cls, pos: 'Position', data: 'Template') -> Self:
        value_data = SingleValue.try_from(data)
        return cls(pos, value_data.value)

    def create_constraints(self, board: 'Board', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)

        nei_pos = [pos for pos in self.pos.neighbors(2) if board.is_valid(pos)]
        nei_2m_var = board.batch(nei_pos, mode="var", special=NAME_2Minf)
        nei_pos_var = board.batch(nei_pos, mode="var")
        if self.count == -1:
            model.add_bool_or(nei_2m_var).only_enforce_if(s)
        else:
            model.add(sum(nei_pos_var) == self.count).only_enforce_if(s)
            model.add_bool_and([var.Not() for var in nei_2m_var]).only_enforce_if(s)
