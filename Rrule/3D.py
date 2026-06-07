"""
[3D] 辞典：所有雷从左到右，从上到下依次标号。线索表示周围八格的雷的标号之和
"""

from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue
from minesweepervariants.board import JSONObject, Board
from ....utils.tool import get_logger


from minesweepervariants.abs.Lrule import AbstractMinesRule
from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue
from minesweepervariants.board import JSONObject, Board, Position
from minesweepervariants.impl.summon.solver import Switch
from ortools.sat.python.cp_model import CpModel


class Rule3D(AbstractMinesRule):
    id = "3D"
    name = "Dict"
    name.zh_CN = "辞典"
    doc = "All mines are numbered from left to right, top to bottom. Clue indicates the sum of mine indices in the eight surrounding cells"
    doc.zh_CN = "所有雷从左到右，从上到下依次标号。线索表示周围八格的雷的标号之和"
    lib_only = True
    tags = ["Creative", "Global", "Number Clue", "Mine-Value"]
    creation_time = "2025-08-23"
    author = ("", 0)

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        self.onboard_init(board)

    def onboard_init(self, board: 'Board'):
        self.dict = {}
        def get_type(board: 'Board', pos: 'Position', *args, **kwargs):
            if self.dict:
                return self.dict.get(str(pos), 0)
            for key in board.get_interactive_keys():
                self.dict = {}
                for _pos, _ in board("F", key=key):
                    if board.get_type(_pos, special="raw") == "F":
                        self.dict[str(_pos)] = len(self.dict) + 1
            print("3D dict:", self.dict)
            return self.dict.get(str(pos), 0)

        board.register_type_special('3D', get_type)



    def create_constraints(self, board: 'Board', switch):
        model = board.get_model()
        s = switch.get(model, self)
        key = board.get_interactive_keys()[0]  # 仅支持单板规则
        row = board.boundary(key).row + 1
        col = board.boundary(key).col + 1
        N = row * col
        m = [board.get_variable(board.get_pos(r, c, key)) for r in range(row) for c in range(col)]      # 雷格变量
        P = [model.NewIntVar(0, N, f"[3D]P{i}") for i in range(N)]                                                 # 前缀雷计数

        # 连接 P 与 m（P 是 m 的前缀和）
        # P[0] = m[0]; P[i] = P[i-1] + m[i]
        model.Add(P[0] == m[0]).OnlyEnforceIf(s)
        for i in range(1, N):
            model.Add(P[i] == P[i-1] + m[i]).OnlyEnforceIf(s)

        for r in range(row):
            for c in range(col):
                idx = r * col + c
                pos = board.get_pos(r, c, key)
                raw = board.get_variable(pos, special='raw')
                det = board.get_variable(pos, special='3D')

                model.Add(det == P[idx]).OnlyEnforceIf([raw, s])
                model.Add(det == 0).OnlyEnforceIf([raw.Not(), s])
