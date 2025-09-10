from typing import List, Dict

from ortools.sat.python.cp_model import CpModel
from minesweepervariants.abs.Rrule import AbstractClueValue, AbstractClueRule
from minesweepervariants.abs.board import AbstractPosition, AbstractBoard
from ....utils.tool import get_random, get_logger
from ....utils.image_create import get_image, get_text, get_row, get_col, get_dummy
from ....utils.web_template import StrWithArrow

class Rule1F(AbstractClueRule):
    name = ["1F", "远视", "Farsight"]
    doc = "线索表示朝向箭头方向到达雷或题板边缘时，垂直与箭头方向的连续非雷格数量"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        random = get_random()
        for pos, _ in board("N"):
            # 随机选择一个方向 (0:上, 1:右, 2:下, 3:左)
            direction = random.randint(0, 3)
            sight_pos = pos.clone()
            while board.get_type(sight_pos) in ["N", "C"]:
                if direction == 0:
                    sight_pos = sight_pos.up()
                elif direction == 1:
                    sight_pos = sight_pos.right()
                elif direction == 2:
                    sight_pos = sight_pos.down()
                elif direction == 3:
                    sight_pos = sight_pos.left()
            
            start_count_pos = sight_pos
            if direction == 0:
                start_count_pos = sight_pos.down()
            elif direction == 1:
                start_count_pos = sight_pos.left()
            elif direction == 2:
                start_count_pos = sight_pos.up()
            elif direction == 3:
                start_count_pos = sight_pos.right()
            upper_scan_pos, lower_scan_pos = start_count_pos.clone(), start_count_pos.clone()
            while board.get_type(upper_scan_pos) in ["N", "C"]:
                if direction % 2 == 0:
                    upper_scan_pos = upper_scan_pos.right()
                else:
                    upper_scan_pos = upper_scan_pos.up()
            while board.get_type(lower_scan_pos) in ["N", "C"]:
                if direction % 2 == 0:
                    lower_scan_pos = lower_scan_pos.left()
                else:
                    lower_scan_pos = lower_scan_pos.down()
            count = abs(upper_scan_pos.x - lower_scan_pos.x) + abs(upper_scan_pos.y - lower_scan_pos.y) - 1
            board.set_value(pos, Value1F(pos, direction=direction, count=count))

        return board

class Value1F(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', direction: int = 0, count: int = 0, code: bytes = None):
        super().__init__(pos, code)
        if (code is not None):
            self.direction = code[0]
            self.count = code[1]
        else:
            self.direction = direction
            self.count = count

    def __repr__(self):
        direction_symbols = ['↑', '→', '↓', '←']
        return f"{self.count}{direction_symbols[self.direction]}"
    
    @classmethod
    def type(cls) -> bytes:
        return Rule1F.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.direction, self.count])
    
    def web_component(self, board) -> Dict:
        """生成可视化组件"""
        return StrWithArrow(str(self.count), ["up", "right", "down", "left"][self.direction])

    def compose(self, board) -> Dict:
        """生成可视化组件"""
        direction_images = ['up', 'right', 'down', 'left']

        if self.direction in [0, 2]:  # 上或下
            return get_row(
                get_dummy(width=0.15),
                get_image(direction_images[self.direction]),
                get_dummy(width=-0.15),
                get_text(str(self.count)),
                get_dummy(width=0.15),
            )
        else:  # 左或右
            return get_col(
                get_image(
                    direction_images[self.direction],
                    image_height=0.4,
                ),
                get_dummy(height=-0.1),
                get_text(str(self.count))
            )

    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition'] | None:
        path = [self.pos]
        path_defined = True
        moves = [
            lambda p: p.up(),
            lambda p: p.right(),
            lambda p: p.down(),
            lambda p: p.left()
        ]
        while board.in_bounds(path[-1]):
            path.append(moves[self.direction](path[-1]))
            type = board.get_type(path[-1])
            if type == "F":
                break
            elif type == "N":
                path_defined = False
        if not path_defined:
            return path[1:-1]
        else:
            perpendicular_start_pos = path[-2]
            if self.direction in (0, 2):
                perpendicular_moves = [lambda p: p.left(), lambda p: p.right()]
            else:
                perpendicular_moves = [lambda p: p.up(), lambda p: p.down()]
            perpendicular_path = []
            for move in perpendicular_moves:
                curr = move(perpendicular_start_pos)
                while board.in_bounds(curr) and board.get_type(curr) != "F":
                    perpendicular_path.append(curr)
                    curr = move(curr)
            return perpendicular_path + path[1:-1]

    def create_constraints(self, board: 'AbstractBoard', switch):
        def add_perpendicular_constraints(model: CpModel, board: AbstractBoard, start_pos, d, target, cond_var, switch_var):
            # 方向 d 的垂直方向
            if d in (0, 2):  # 上下走，检查左右
                moves = [lambda p: p.left(), lambda p: p.right()]
            else:            # 左右走，检查上下
                moves = [lambda p: p.up(), lambda p: p.down()]

            cont_vars = []
            for move in moves:
                prev_cont_var = None
                curr = move(start_pos)
                while board.in_bounds(curr):
                    cont_var = model.NewBoolVar(f"cont_{curr}")
                    if (prev_cont_var is None):
                        # 连续非雷段的起始：当前位置是非雷
                        model.Add(cont_var == 1).OnlyEnforceIf([board.get_variable(curr).Not(), switch_var])
                        model.Add(cont_var == 0).OnlyEnforceIf([board.get_variable(curr), switch_var])
                    else:
                        # 连续非雷段的延续：前一个位置在连续非雷段，且当前位置是非雷
                        model.Add(cont_var == 1).OnlyEnforceIf([prev_cont_var, board.get_variable(curr).Not(), switch_var])
                        model.Add(cont_var == 0).OnlyEnforceIf([prev_cont_var.Not(), switch_var])
                        model.Add(cont_var == 0).OnlyEnforceIf([board.get_variable(curr), switch_var])
                    cont_vars.append(cont_var)
                    prev_cont_var = cont_var
                    curr = move(curr)
            model.Add(sum(cont_vars) + 1 == target).OnlyEnforceIf([cond_var, switch_var])

        model = board.get_model()
        s = switch.get(model, self)

        start = self.pos
        d = self.direction
        target = self.count

        # 沿着方向收集路径
        path = [start]
        cur = start
        while True:
            cur = (cur.up() if d == 0 else
                cur.right() if d == 1 else
                cur.down() if d == 2 else
                cur.left())
            if not board.in_bounds(cur):
                break
            path.append(cur)

        # 终点变量：路径上的每一个格子 + 出界
        stop_vars = []
        for idx, p in enumerate(path[1:]):
            stop_var = model.NewBoolVar(f"stop_{idx}_{p}")
            stop_vars.append(stop_var)

        # 出界终点
        stop_var_out = model.NewBoolVar("stop_out")
        stop_vars.append(stop_var_out)

        # 恰好一个终点
        model.Add(sum(stop_vars) == 1).OnlyEnforceIf(s)

        # 路径内的终点约束
        for idx, stop_var in enumerate(stop_vars[:-1]):
            stop_cell = board.get_variable(path[idx + 1])

            # 终点必须是雷
            model.Add(stop_cell == 1).OnlyEnforceIf([stop_var, s])

            # 终点之前的格子必须非雷
            for before in path[:idx + 1]:
                model.Add(board.get_variable(before) == 0).OnlyEnforceIf([stop_var, s])

            # 计算垂直方向连续非雷
            add_perpendicular_constraints(model, board, path[idx], d, target, stop_var, s)

        # 出界终点约束
        # 出界时路径上的所有格子必须非雷
        for p in path:
            model.Add(board.get_variable(p) == 0).OnlyEnforceIf(stop_var_out).OnlyEnforceIf(s)

        # 从出界点往垂直方向看，即从路径的最后一个格子计算
        if path:
            last_pos = path[-1]
            add_perpendicular_constraints(model, board, last_pos, d, target, stop_var_out, s)


