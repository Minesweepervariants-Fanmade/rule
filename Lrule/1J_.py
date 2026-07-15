"""
[*1J] 任意四连通的雷格区域不能组成矩形（包括1*1与1*2）
实现：对于任何矩形区域，如果其内部全是雷，则其外部相邻位置（上下左右）必须至少有一个雷。
这样，矩形区域就不会成为孤立的连通块，从而避免了矩形雷区的出现。
"""

from typing import Optional, List
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board, MASTER_BOARD_KEY
from minesweepervariants.position import Position


class Star1J(AbstractMinesRule):
    id = "*1J"
    aliases = ("1J*",)
    name = "No Rectangular Mine Region"
    name.zh_CN = "禁止矩形雷区"
    doc = "Any 4-connected mine region cannot form a rectangle (including 1x1 and 1x2)."
    doc.zh_CN = "任意四连通的雷格区域不能组成矩形（包括1*1与1*2）"
    author = ("波常未来", 81500378)
    tags = ["Anti-Construction", "Global"]
    creation_time = "2026-07-16"

    def create_constraints(self, board: Board, switch):
        model = board.get_model()
        if model is None:
            return

        cols, rows = board.get_config(config_name="size", board_key=MASTER_BOARD_KEY)

        # 获取规则开关变量，并将所有约束关联到该开关
        rule_switch = switch.get(model, self)

        # 枚举所有可能的矩形区域
        for r1 in range(rows):
            for c1 in range(cols):
                for r2 in range(r1, rows):
                    for c2 in range(c1, cols):
                        # 收集矩形内所有有效位置的变量
                        vars_in_rect: List = []
                        all_valid = True
                        for r in range(r1, r2 + 1):
                            for c in range(c1, c2 + 1):
                                pos = Position(c, r, MASTER_BOARD_KEY)
                                if not board.is_valid(pos):
                                    all_valid = False
                                    break
                                var = board.get_variable(pos)
                                if var is None:
                                    all_valid = False
                                    break
                                vars_in_rect.append(var)
                            if not all_valid:
                                break
                        if not all_valid or not vars_in_rect:
                            continue

                        # 辅助变量：矩形内所有格子都是雷
                        all_mines = model.NewBoolVar(f"all_mines_{r1}_{c1}_{r2}_{c2}")

                        # 约束1：如果 all_mines 为真，则矩形内所有格子都是雷
                        for var in vars_in_rect:
                            model.Add(var == 1).OnlyEnforceIf([all_mines, rule_switch])

                        # 约束2：如果矩形内所有格子都是雷，则 all_mines 为真
                        # 即：至少有一个格子不是雷 或 all_mines 为真
                        model.AddBoolOr([var.Not() for var in vars_in_rect] + [all_mines]).OnlyEnforceIf(rule_switch)

                        # 收集外部相邻位置的变量（上、下、左、右）
                        external_vars: List = []
                        # 上方相邻
                        if r1 > 0:
                            for c in range(c1, c2 + 1):
                                pos = Position(c, r1 - 1, MASTER_BOARD_KEY)
                                if board.is_valid(pos):
                                    var = board.get_variable(pos)
                                    if var is not None:
                                        external_vars.append(var)
                        # 下方相邻
                        if r2 < rows - 1:
                            for c in range(c1, c2 + 1):
                                pos = Position(c, r2 + 1, MASTER_BOARD_KEY)
                                if board.is_valid(pos):
                                    var = board.get_variable(pos)
                                    if var is not None:
                                        external_vars.append(var)
                        # 左方相邻
                        if c1 > 0:
                            for r in range(r1, r2 + 1):
                                pos = Position(c1 - 1, r, MASTER_BOARD_KEY)
                                if board.is_valid(pos):
                                    var = board.get_variable(pos)
                                    if var is not None:
                                        external_vars.append(var)
                        # 右方相邻
                        if c2 < cols - 1:
                            for r in range(r1, r2 + 1):
                                pos = Position(c2 + 1, r, MASTER_BOARD_KEY)
                                if board.is_valid(pos):
                                    var = board.get_variable(pos)
                                    if var is not None:
                                        external_vars.append(var)

                        # 约束3：如果 all_mines 为真，则外部至少有一个雷
                        # 等价于：not all_mines OR (外部雷的 OR)
                        if external_vars:
                            model.AddBoolOr([all_mines.Not()] + external_vars).OnlyEnforceIf(rule_switch)
                        else:
                            # 如果没有外部相邻位置，则 all_mines 必须为假
                            model.Add(all_mines == 0).OnlyEnforceIf(rule_switch)

    def suggest_total(self, info: dict):
        """不强制特定总数。"""
        pass

    def init_board(self, board: Board) -> bool:
        return True

    def init_clear(self, board: Board) -> None:
        pass

    def combine(self, other) -> Optional['Star1J']:
        return None

    def get_deps(self) -> list[str]:
        return []
