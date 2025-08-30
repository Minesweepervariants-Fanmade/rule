#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
[1X-] 残缺十字 (Pawn)：线索表示朝向一个方向的两个格子中的雷数，线索会标注出方向
"""
from typing import List, Dict

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition
from ....utils.image_create import get_image, get_text, get_row, get_col, get_dummy
from ....utils.impl_obj import MINES_TAG, VALUE_QUESS
from ....utils.tool import get_random, get_logger


class Rule1X_(AbstractClueRule):
    name = ["1X-", "残缺十字", "Pawn"]
    doc = "线索表示朝向一个方向的两个格子中的雷数，线索会标注出方向"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        logger = get_logger()
        random = get_random()

        for pos, _ in board("N"):
            # 随机选择一个方向 (0:上, 1:右, 2:下, 3:左)
            direction = random.randint(0, 3)

            # 获取该方向上的两个格子
            target_positions = []
            if direction == 0:  # 上
                target_positions = [pos.up(), pos.up().up()]
            elif direction == 1:  # 右
                target_positions = [pos.right(), pos.right().right()]
            elif direction == 2:  # 下
                target_positions = [pos.down(), pos.down().down()]
            elif direction == 3:  # 左
                target_positions = [pos.left(), pos.left().left()]

            # 计算有效格子中的雷数
            mine_count = 0
            for target_pos in target_positions:
                if board.in_bounds(target_pos) and board.get_type(target_pos) == "F":
                    mine_count += 1

            board.set_value(pos, Value1X_(pos, count=mine_count, direction=direction))
            logger.debug(f"Set {pos} to 1X-[{mine_count}] direction {direction}")

        return board


class Value1X_(AbstractClueValue):
    def __init__(self, pos: AbstractPosition, count: int = 0, direction: int = 0, code: bytes = None):
        super().__init__(pos, code)
        if code is not None:
            # 从字节码解码
            self.count = code[0]
            self.direction = code[1]  # 0:上, 1:右, 2:下, 3:左
        else:
            # 直接初始化
            self.count = count
            self.direction = direction

        # 计算目标格子位置
        self.target_positions = []
        if self.direction == 0:  # 上
            self.target_positions = [self.pos.up(), self.pos.up().up()]
        elif self.direction == 1:  # 右
            self.target_positions = [self.pos.right(), self.pos.right().right()]
        elif self.direction == 2:  # 下
            self.target_positions = [self.pos.down(), self.pos.down().down()]
        elif self.direction == 3:  # 左
            self.target_positions = [self.pos.left(), self.pos.left().left()]

    def __repr__(self):
        direction_symbols = ['↑', '→', '↓', '←']
        return f"{self.count}{direction_symbols[self.direction]}"

    def __str__(self):
        direction_symbols = ['↑', '→', '↓', '←']
        return f"{self.count}{direction_symbols[self.direction]}"

    @classmethod
    def type(cls) -> bytes:
        return b'1X-'

    def code(self) -> bytes:
        return bytes([self.count, self.direction])

    def high_light(self, board: 'AbstractBoard') -> List['AbstractPosition']:
        return self.target_positions

    def web_component(self, board) -> Dict:
        direction_images = ['up', 'right', 'down', 'left']

        if self.direction in [0, 2]:  # 上或下
            if self.count == 1:
                return get_row(
                        get_dummy(width=0.175),
                        get_text("1"),
                        get_image(direction_images[self.direction]),
                        get_dummy(width=0.175),
                    )

            return get_row(
                    get_text(str(self.count)),
                    get_image(direction_images[self.direction]),
                    spacing=-0.1,
                )
        else:  # 左或右
            return get_col(
                    get_dummy(height=0.1),
                    get_image(
                        direction_images[self.direction],
                        image_height=0.2,
                        image_width=0.7
                    ),
                    get_dummy(height=-0.05),
                    get_text(str(self.count)),
                    get_dummy(height=0.2)
                )

    def compose(self, board) -> Dict:
        """生成可视化组件"""
        direction_images = ['up', 'right', 'down', 'left']

        if self.direction in [0, 2]:  # 上或下
            if self.count == 1:
                return get_row(
                        get_dummy(width=0.175),
                        get_text("1"),
                        get_image(direction_images[self.direction]),
                        get_dummy(width=0.175),
                    )

            return get_row(
                    get_text(str(self.count)),
                    get_image(direction_images[self.direction]),
                    spacing=-0.1,
                )
        else:  # 左或右
            return get_col(
                    get_dummy(height=0.1),
                    get_image(
                        direction_images[self.direction],
                        image_height=0.2,
                        image_width=0.7
                    ),
                    get_dummy(height=-0.05),
                    get_text(str(self.count)),
                    get_dummy(height=0.2)
                )

    def deduce_cells(self, board: 'AbstractBoard') -> bool:
        """逻辑推理"""
        # 收集有效的目标格子
        valid_targets = []
        type_dict = {"N": [], "F": []}

        for target_pos in self.target_positions:
            if board.in_bounds(target_pos):
                valid_targets.append(target_pos)
                t = board.get_type(target_pos)
                if t in ("", "C"):
                    continue
                type_dict[t].append(target_pos)

        if not valid_targets:
            return False

        n_num = len(type_dict["N"])
        f_num = len(type_dict["F"])

        if n_num == 0:
            return False

        # 如果雷数已满，剩余格子都是安全的
        if f_num == self.count:
            for pos in type_dict["N"]:
                board.set_value(pos, VALUE_QUESS)
            return True

        # 如果所有格子都必须是雷才能满足条件
        if f_num + n_num == self.count:
            for pos in type_dict["N"]:
                board.set_value(pos, MINES_TAG)
            return True

        return False

    def create_constraints(self, board: 'AbstractBoard', switch):
        """创建CP-SAT约束"""
        model = board.get_model()
        s = switch.get(model, self)

        # 收集有效目标格子的变量
        target_vars = []
        for target_pos in self.target_positions:
            if board.in_bounds(target_pos):
                var = board.get_variable(target_pos)
                target_vars.append(var)

        # 添加约束：目标格子中的雷数等于count
        if target_vars:
            model.Add(sum(target_vars) == self.count).OnlyEnforceIf(s)
