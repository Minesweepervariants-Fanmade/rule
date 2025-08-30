#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/04 07:39
# @Author  : Wu_RH
# @FileName: 4V.py
"""
[4V2E'2I']映射自指残缺(2X'plus+2E'+2I'): 字母X是两个题板中相同位置为中心其中一个的3x3区域中某?格的雷总数为N。则该对应位置所属的题板在标有X=N的位置必然是雷, 且?格的位置全局共享
(注:生成不知道是不是概率问题 会出现大量的生成失败 不过也不是人玩的反正 加个-r估计会好)
"""
from .....abs.Rrule import AbstractClueRule, AbstractClueValue
from .....abs.board import AbstractBoard, AbstractPosition, MASTER_BOARD
from .....utils.impl_obj import VALUE_QUESS, MINES_TAG, VALUE_CIRCLE, VALUE_CROSS
from .....utils.tool import get_random, get_logger
from . import BOARD_NAME_4V

NAME = BOARD_NAME_4V
NAME_4V_2Ip = "4V2I'"
ALPHABET = "ABCDEFGHIJ"


class Rule4V2Ep2Ip(AbstractClueRule):
    name = ["4V2E'2I'", "自指残缺映射"]
    doc = "字母X是两个题板中相同位置为中心其中一个的3x3区域中某?格的雷总数为N。则该对应位置所属的题板在标有X=N的位置必然是雷, 且?格的位置全局共享"

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        size = (board.boundary().x + 1, board.boundary().y + 1)
        board.generate_board(NAME, size)
        board.set_config(NAME, "interactive", True)
        board.set_config(NAME, "row_col", True)
        board.set_config(NAME, "VALUE", VALUE_QUESS)
        board.set_config(NAME, "MINES", MINES_TAG)
        board.set_config(NAME, "pos_label", True)
        board.set_config(MASTER_BOARD, "pos_label", True)
        board.generate_board(NAME_4V_2Ip, (3, 3))

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        def apply_offsets(_pos: AbstractPosition):
            nonlocal offsets
            result = []
            for dpos in offsets:
                result.append(_pos.deviation(dpos))
            return result

        random = get_random()

        pos_list = [pos for pos, _ in board("N", key=NAME_4V_2Ip)]
        pos_list = random.sample(pos_list, int(random.random() * 6 + 3))
        offsets = []
        for pos in pos_list:
            board[pos] = VALUE_CIRCLE
            offsets.append(pos.up().left())
        for pos, _ in board("N", key=NAME_4V_2Ip):
            board[pos] = VALUE_CROSS

        letter_map_a = {i: [] for i in range(10)}
        for pos, _ in board("F", key=MASTER_BOARD):
            if pos.y > 9:
                continue
            letter = ALPHABET[pos.y]
            if pos.x not in letter_map_a:
                letter_map_a[pos.x] = []
            letter_map_a[pos.x].append(letter)

        letter_map_b = {i: [] for i in range(10)}
        for pos, _ in board("F", key=NAME):
            if pos.y > 9:
                continue
            letter = ALPHABET[pos.y]
            if pos.x not in letter_map_b:
                letter_map_b[pos.x] = []
            letter_map_b[pos.x].append(letter)

        for pos, _ in board(key=MASTER_BOARD):
            neighbors_list = []
            for _key in [MASTER_BOARD, NAME]:
                _pos = pos.clone()
                _pos.board_key = _key
                neighbors_list.append(apply_offsets(_pos))
            values = [board.batch(positions, mode="type").count("F") for positions in neighbors_list]
            values[0] = ALPHABET.index(random.choice(letter_map_a[values[0]])) if letter_map_a[values[0]] else -1
            values[1] = ALPHABET.index(random.choice(letter_map_b[values[1]])) if letter_map_b[values[1]] else -1
            r_value = 0 if random.random() > 0.7 else 1
            _pos.board_key = MASTER_BOARD
            if board.get_type(_pos) != "F":
                obj = Value4V2Ep2Ip(pos=_pos, code=bytes([values[r_value]])) if values[r_value] != -1 else VALUE_QUESS
                board.set_value(_pos, obj)
            _pos.board_key = NAME
            if board.get_type(_pos) != "F":
                obj = Value4V2Ep2Ip(pos=_pos, code=bytes([values[1 - r_value]])) \
                    if values[1 - r_value] != -1 else VALUE_QUESS
                board.set_value(_pos, obj)
        return board

    def suggest_total(self, info: dict):
        ub = 0
        for key in info["interactive"]:
            size = info["size"][key]
            ub += size[0] * size[1]
        info["soft_fn"](ub * 0.4)

    def init_clear(self, board: 'AbstractBoard'):
        for pos, obj in board(mode="object", key=NAME_4V_2Ip):
            board[pos] = None


class Value4V2Ep2Ip(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        self.value = code[0]
        self.pos = pos

    @classmethod
    def type(cls) -> bytes:
        return Rule4V2Ep2Ip.name[0].encode("ascii")

    def __repr__(self) -> str:
        return f"{ALPHABET[self.value]}"

    def high_light(self, board: 'AbstractBoard') -> list['AbstractPosition']:
        positions = []
        for pos_key in [MASTER_BOARD, BOARD_NAME_4V]:
            self_pos = self.pos.clone()
            self_pos.board_key = pos_key
            for pos, _ in board("NF", key=NAME_4V_2Ip):
                _pos = self_pos.deviation(pos.shift(1, -1))
                if board.in_bounds(_pos):
                    positions.append(_pos)
        return positions

    def create_constraints(self, board: 'AbstractBoard', switch):
        # 初始化模型
        model = board.get_model()
        s = switch.get(model, self)
        # 初始化日志
        logger = get_logger()

        sum_var = []
        for key in [MASTER_BOARD, NAME]:
            _pos = self.pos.clone()
            _pos.board_key = key

            b = model.NewBoolVar(f"[{Rule4V2Ep2Ip.name}]tmp")
            sum_var.append(b)

            # 初始化位置对象 位于X列
            pos = board.get_pos(0, self.value, key)
            # 获取该列的所有位置
            line = board.get_col_pos(pos)
            # 获取该列的所有变量
            line_vars = board.batch(line, mode="variable")

            # 初始化对照表
            neighbors = []
            for pos2, obj in board(key=NAME_4V_2Ip):
                # 题板上的位置和共享的偏移位置
                _positions = [_pos.deviation(pos2).up().left(), pos2]
                # 第一个为题板对应的变量 第二个为偏移的变量
                if not board.in_bounds(_positions[0]):
                    continue
                neighbors.append(board.batch(_positions, mode="variable"))

            # 初始化和值
            sum_vers = []
            for var_to_sum, cond in neighbors:
                # 初始化临时变量
                tmp = model.NewBoolVar(f"included_if_{_pos}_{var_to_sum}")
                # 如果偏移变量为真 那么tmp为题板的值
                model.Add(tmp == var_to_sum).OnlyEnforceIf([cond, b, s])
                # 如果偏移变量为假 那么tmp为0
                model.Add(tmp == 0).OnlyEnforceIf([cond.Not(), b, s])
                sum_vers.append(tmp)
                logger.trace(f"[4V2E'2I'] new tempVar: {tmp} = if {cond} -> {var_to_sum}")

            for index in range(min(8, len(line_vars))):
                # 获取该列的X=index的变量
                var = line_vars[index]
                # 如果变量为真 那么sum应该相对 反之亦然
                model.Add(sum(sum_vers) != index).OnlyEnforceIf([var.Not(), b, s])
                logger.trace(f"[4V2E'2I'] sum_tmp != {index} only if not {var}")

        model.AddBoolOr(sum_var).OnlyEnforceIf(s)
        # model.Add(sum(sum_var) == 0)

    def code(self) -> bytes:
        return bytes([self.value])
