"""
[3U] 上上：每列最高的雷视为两个雷（总雷数不受其影响）
"""

from ....abs.board import AbstractBoard
from ....utils.tool import get_logger


from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.impl.summon.solver import Switch
from ortools.sat.python.cp_model import CpModel

class Rule3U(AbstractMinesRule):
    name = ["3U", "上上"]
    doc = "每列最高的雷视为两个雷（总雷数不受其影响）"
    lib_only = True

    def __init__(self, board: AbstractBoard = None, data=None) -> None:
        super().__init__(board, data)
        self.onboard_init(board)

    def onboard_init(self, board: 'AbstractBoard'):
        self.dict = {}
        def get_type(board: 'AbstractBoard', pos: 'AbstractPosition', *args, **kwargs):
            origin = board.get_type(pos, 'raw') == 'F'
            up_pos = pos.up()
            while board.in_bounds(up_pos):
                if (board.get_type(up_pos, 'raw') == 'F'):
                    return origin
                up_pos = up_pos.up()
            return origin * 2

        board.register_type_special('3U', get_type)

    def create_constraints(self, board: AbstractBoard, switch: Switch):
        model = board.get_model()
        for key in board.get_interactive_keys():
            for pos, _ in board(key=key):
                raw = board.get_variable(pos, special='raw')
                ret = board.get_variable(pos, special='3U')
                is_top_pos = model.NewBoolVar(f"is_top_pos_{pos}")
                up_poses = []
                up_pos = pos.up()
                while board.in_bounds(up_pos):
                    up_poses.append(up_pos)
                    up_pos = up_pos.up()
                model.Add(sum(board.batch(up_poses, mode='variable', drop_none=True)) == 0).OnlyEnforceIf(is_top_pos)
                model.AddBoolOr(board.batch(up_poses, mode='variable', drop_none=True)).OnlyEnforceIf(is_top_pos.Not())
                model.Add(ret == raw).OnlyEnforceIf(is_top_pos.Not())
                model.Add(ret == raw * 2).OnlyEnforceIf(is_top_pos)
