"""
[4O] 近视：线索以上下左右箭头而非数字呈现，箭头指向四方向距离其最近的雷，同时存在多个雷距离最近时会显示全部箭头。四方向都不存在雷时显示零。
"""

from typing import Dict

from minesweepervariants.impl.summon.solver import Switch
from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition
from ....utils.image_create import get_dummy, get_image, get_col, get_row, get_text

class Rule4O(AbstractClueRule):
    name = ["4O", "近视", "Myopia"]
    doc = "线索以上下左右箭头而非数字呈现，箭头指向四方向距离其最近的雷，同时存在多个雷距离最近时会显示全部箭头。四方向都不存在雷时显示零。"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        for pos, _ in board("N"):
            # 上方向
            current = pos.up()
            up_distance = 1
            while board.in_bounds(current):
                if board.get_type(current) == "F":
                    break
                current = current.up()
                up_distance += 1
            else:
                up_distance = 1e9

            # 下方向
            current = pos.down()
            down_distance = 1
            while board.in_bounds(current):
                if board.get_type(current) == "F":
                    break
                current = current.down()
                down_distance += 1
            else:
                down_distance = 1e9

            # 左方向
            current = pos.left()
            left_distance = 1
            while board.in_bounds(current):
                if board.get_type(current) == "F":
                    break
                current = current.left()
                left_distance += 1
            else:
                left_distance = 1e9

            # 右方向
            current = pos.right()
            right_distance = 1
            while board.in_bounds(current):
                if board.get_type(current) == "F":
                    break
                current = current.right()
                right_distance += 1
            else:
                right_distance = 1e9

            directions = 0
            min_distance = min(up_distance, down_distance, left_distance, right_distance)
            if min_distance != 1e9:
                if up_distance == min_distance:
                    directions |= 1
                if down_distance == min_distance:
                    directions |= 2
                if left_distance == min_distance:
                    directions |= 4
                if right_distance == min_distance:
                    directions |= 8
            board.set_value(pos, Value4O(pos, bytes([directions])))
        return board

class Value4O(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes):
        super().__init__(pos, code)
        self.directions = code[0] # 位掩码：1-上，2-下，4-左，8-右

    def __repr__(self) -> str:
        if (self.directions == 0):
            return "0"

        dirs = []
        if self.directions & 1:
            dirs.append("↑")
        if self.directions & 2:
            dirs.append("↓")
        if self.directions & 4:
            dirs.append("←")
        if self.directions & 8:
            dirs.append("→")
        return "".join(dirs)

    @classmethod
    def type(cls) -> bytes:
        return b'4O'

    def code(self) -> bytes:
        return bytes([self.directions])

    composes = [
        # 0: 显示零
        get_col(
            get_dummy(height=0.3),
            get_text("0"),
            get_dummy(height=0.3),
        ),
        # 上
        get_col(
            get_dummy(height=0.175),
            get_image("up"),
            get_dummy(height=0.175),
        ),
        # 下
        get_col(
            get_dummy(height=0.175),
            get_image("down"),
            get_dummy(height=0.175),
        ),
        # 上下
        get_col(
            get_dummy(height=0.175),
            get_row(
                get_image("up"),
                get_image("down"),
            ),
            get_dummy(height=0.175),
        ),
        # 左
        get_col(
            get_dummy(height=0.175),
            get_image("left"),
            get_dummy(height=0.175),
        ),
        # 上左
        get_col(
            get_dummy(height=0.175),
            get_row(
                get_image("left", image_height=0.25),
                get_image("up"),
            ),
            get_dummy(height=0.175),
        ),
        # 下左
        get_col(
            get_dummy(height=0.175),
            get_row(
                get_image("left", image_height=0.25),
                get_image("down"),
            ),
            get_dummy(height=0.175),
        ),
        # 上下左
        get_row(
            get_image("left", image_height=0.25),
            get_col(
                get_image("up"),
                get_image("down"),
            )
        ),
        # 右
        get_col(
            get_dummy(height=0.175),
            get_image("right"),
            get_dummy(height=0.175),
        ),
        # 上右
        get_col(
            get_dummy(height=0.175),
            get_row(
                get_image("up"),
                get_image("right", image_height=0.25),
            ),
            get_dummy(height=0.175),
        ),
        # 下右
        get_col(
            get_dummy(height=0.175),
            get_row(
                get_image("down"),
                get_image("right", image_height=0.25),
            ),
            get_dummy(height=0.175),
        ),
        # 上下右
        get_row(
            get_col(
                get_image("up"),
                get_image("down"),
            ),
            get_image("right", image_height=0.25),
        ),
        # 左右
        get_col(
            get_dummy(height=0.175),
            get_row(
                get_image("left"),
                get_image("right")
            ),
            get_dummy(height=0.175),
        ),
        # 上左右
        get_col(
            get_image("up"),
            get_row(
                get_image("left"),
                get_image("right")
            )
        ),
        # 下左右
        get_col(
            get_row(
                get_image("left"),
                get_image("right")
            ),
            get_image("down"),
        ),
        # 上下左右
        get_col(
            get_row(
                get_image("up"),
                get_image("down")
            ),
            get_row(
                get_image("left"),
                get_image("right")
            )
        )
    ]

    def compose(self, board) -> Dict:
        return Value4O.composes[self.directions]
    
    def create_constraints(self, board: AbstractBoard, switch: Switch):
        model = board.get_model()
        s = switch.get(model, self)
        n = board.boundary(self.pos.board_key).x + 1
        sight_vars = [
            model.NewIntVar(0, n + 1, f"4O_up_{self.pos}"),
            model.NewIntVar(0, n + 1, f"4O_down_{self.pos}"),
            model.NewIntVar(0, n + 1, f"4O_left_{self.pos}"),
            model.NewIntVar(0, n + 1, f"4O_right_{self.pos}"),
        ]
        moves = [
            lambda p: p.up(),
            lambda p: p.down(),
            lambda p: p.left(),
            lambda p: p.right()
        ]
        for sight_var, move in zip(sight_vars, moves):
            prev_cont_var = None
            curr = move(self.pos)
            cont_vars = []
            while board.in_bounds(curr):
                cont_var = model.NewBoolVar(f"cont_{curr}")
                if (prev_cont_var is None):
                    # 连续非雷段的起始：当前位置是非雷
                    model.Add(cont_var == 1).OnlyEnforceIf([board.get_variable(curr).Not(), s])
                    model.Add(cont_var == 0).OnlyEnforceIf([board.get_variable(curr), s])
                else:
                    # 连续非雷段的延续：前一个位置在连续非雷段，且当前位置是非雷
                    model.Add(cont_var == 1).OnlyEnforceIf([prev_cont_var, board.get_variable(curr).Not(), s])
                    model.Add(cont_var == 0).OnlyEnforceIf([prev_cont_var.Not(), s])
                    model.Add(cont_var == 0).OnlyEnforceIf([board.get_variable(curr), s])
                cont_vars.append(cont_var)
                prev_cont_var = cont_var
                curr = move(curr)
            out_of_bounds_var = model.NewBoolVar("out_of_bounds")
            model.Add(sum(cont_vars) == len(cont_vars)).OnlyEnforceIf(out_of_bounds_var, s)
            model.Add(sum(cont_vars) < len(cont_vars)).OnlyEnforceIf(out_of_bounds_var.Not(), s)
            model.Add(sum(cont_vars) == sight_var).OnlyEnforceIf(out_of_bounds_var.Not(), s)
            model.Add(sight_var == n + 1).OnlyEnforceIf(out_of_bounds_var, s)

        match self.directions:
            case 0:
                for sight_var in sight_vars:
                    model.Add(sight_var == n + 1).OnlyEnforceIf(s)
            case 1: # 上
                model.Add(sight_vars[0] < sight_vars[1]).OnlyEnforceIf(s)
                model.Add(sight_vars[0] < sight_vars[2]).OnlyEnforceIf(s)
                model.Add(sight_vars[0] < sight_vars[3]).OnlyEnforceIf(s)   
            case 2: # 下
                model.Add(sight_vars[1] < sight_vars[0]).OnlyEnforceIf(s)
                model.Add(sight_vars[1] < sight_vars[2]).OnlyEnforceIf(s)
                model.Add(sight_vars[1] < sight_vars[3]).OnlyEnforceIf(s)
            case 3: # 上下
                model.Add(sight_vars[0] == sight_vars[1]).OnlyEnforceIf(s)
                model.Add(sight_vars[0] < sight_vars[2]).OnlyEnforceIf(s)
                model.Add(sight_vars[0] < sight_vars[3]).OnlyEnforceIf(s)
            case 4: # 左
                model.Add(sight_vars[2] < sight_vars[0]).OnlyEnforceIf(s)
                model.Add(sight_vars[2] < sight_vars[1]).OnlyEnforceIf(s)
                model.Add(sight_vars[2] < sight_vars[3]).OnlyEnforceIf(s)
            case 5: # 上左
                model.Add(sight_vars[0] == sight_vars[2]).OnlyEnforceIf(s)
                model.Add(sight_vars[0] < sight_vars[1]).OnlyEnforceIf(s)
                model.Add(sight_vars[0] < sight_vars[3]).OnlyEnforceIf(s)
            case 6: # 下左
                model.Add(sight_vars[1] == sight_vars[2]).OnlyEnforceIf(s)
                model.Add(sight_vars[1] < sight_vars[0]).OnlyEnforceIf(s)
                model.Add(sight_vars[1] < sight_vars[3]).OnlyEnforceIf(s)
            case 7: # 上下左
                model.Add(sight_vars[0] == sight_vars[1]).OnlyEnforceIf(s)
                model.Add(sight_vars[0] == sight_vars[2]).OnlyEnforceIf(s)
                model.Add(sight_vars[0] < sight_vars[3]).OnlyEnforceIf(s)
            case 8: # 右
                model.Add(sight_vars[3] < sight_vars[0]).OnlyEnforceIf(s)
                model.Add(sight_vars[3] < sight_vars[1]).OnlyEnforceIf(s)
                model.Add(sight_vars[3] < sight_vars[2]).OnlyEnforceIf(s)
            case 9: # 上右
                model.Add(sight_vars[0] == sight_vars[3]).OnlyEnforceIf(s)
                model.Add(sight_vars[0] < sight_vars[1]).OnlyEnforceIf(s)
                model.Add(sight_vars[0] < sight_vars[2]).OnlyEnforceIf(s)
            case 10: # 下右
                model.Add(sight_vars[1] == sight_vars[3]).OnlyEnforceIf(s)
                model.Add(sight_vars[1] < sight_vars[0]).OnlyEnforceIf(s)
                model.Add(sight_vars[1] < sight_vars[2]).OnlyEnforceIf(s)
            case 11: # 上下右
                model.Add(sight_vars[0] == sight_vars[1]).OnlyEnforceIf(s)
                model.Add(sight_vars[0] == sight_vars[3]).OnlyEnforceIf(s)
                model.Add(sight_vars[0] < sight_vars[2]).OnlyEnforceIf(s)
            case 12: # 左右
                model.Add(sight_vars[2] == sight_vars[3]).OnlyEnforceIf(s)
                model.Add(sight_vars[2] < sight_vars[0]).OnlyEnforceIf(s)
                model.Add(sight_vars[2] < sight_vars[1]).OnlyEnforceIf(s)
            case 13: # 上左右
                model.Add(sight_vars[0] == sight_vars[2]).OnlyEnforceIf(s)
                model.Add(sight_vars[0] == sight_vars[3]).OnlyEnforceIf(s)
                model.Add(sight_vars[0] < sight_vars[1]).OnlyEnforceIf(s)
            case 14: # 下左右
                model.Add(sight_vars[1] == sight_vars[2]).OnlyEnforceIf(s)
                model.Add(sight_vars[1] == sight_vars[3]).OnlyEnforceIf(s)
                model.Add(sight_vars[1] < sight_vars[0]).OnlyEnforceIf(s)
            case 15: # 上下左右
                model.Add(sight_vars[0] == sight_vars[1]).OnlyEnforceIf(s)
                model.Add(sight_vars[0] == sight_vars[2]).OnlyEnforceIf(s)
                model.Add(sight_vars[0] == sight_vars[3]).OnlyEnforceIf(s)
                
    
        
        