"""
[3D] 辞典：所有雷从左到右，从上到下依次标号。线索表示周围八格的雷的标号之和
"""

from ....abs.board import AbstractBoard
from ....utils.tool import get_logger


from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.impl.summon.solver import Switch
from ortools.sat.python.cp_model import CpModel


class Rule3D(AbstractMinesRule):
    name = ["3D", "辞典", "Dict"]
    doc = "所有雷从左到右，从上到下依次标号。线索表示周围八格的雷的标号之和"
    lib_only = True

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        self.onboard_init(board)

    def onboard_init(self, board: 'AbstractBoard'):
        self.dict = {}
        def get_type(board: 'AbstractBoard', pos: 'AbstractPosition', *args, **kwargs):
            if self.dict:
                return self.dict.get(str(pos), 0)
            for key in board.get_interactive_keys():
                self.dict = {}
                x = board.boundary(key).x + 1
                y = board.boundary(key).y + 1
                for i in range(x):
                    for j in range(y):
                        pos = board.get_pos(i, j, key)
                        if board.get_type(pos, special="raw") == "F":
                            self.dict[str(pos)] = len(self.dict) + 1
            print("3D dict:", self.dict)
            return self.dict.get(str(pos), 0)

        board.register_type_special('3D', get_type)



    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        key = board.get_interactive_keys()[0]  # 仅支持单板规则
        x = board.boundary(key).x + 1
        y = board.boundary(key).y + 1
        N = x * y
        m = [board.get_variable(board.get_pos(i, j, key)) for i in range(x) for j in range(y)]      # 雷格变量
        P = [model.NewIntVar(0, N, f"[3D]P{i}") for i in range(N)]                                                 # 前缀雷计数

        # 连接 P 与 m（P 是 m 的前缀和）
        # P[0] = m[0]; P[i] = P[i-1] + m[i]
        model.Add(P[0] == m[0]).OnlyEnforceIf(s)
        for i in range(1, N):
            model.Add(P[i] == P[i-1] + m[i]).OnlyEnforceIf(s)

        for i in range(x):
            for j in range(y):
                idx = i * y + j
                pos = board.get_pos(i, j, key)
                raw = board.get_variable(pos, special='raw')
                det = board.get_variable(pos, special='3D')

                model.Add(det == P[idx]).OnlyEnforceIf([raw, s])
                model.Add(det == 0).OnlyEnforceIf([raw.Not(), s])
