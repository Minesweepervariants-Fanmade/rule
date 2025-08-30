#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/07 19:57
# @Author  : Wu_RH
# @FileName: 3P.py
"""
[3](暂定):作者曾经在主群透露过的内容 雷指向的方向存在n个雷(不包括自己)
"""
from typing import Dict

from ....abs.Mrule import AbstractMinesClueRule, AbstractMinesValue
from ....abs.board import AbstractPosition, AbstractBoard
from ....utils.image_create import get_dummy, get_image, get_col, get_row
from ....utils.image_create import get_text as _get_text
from ....utils.tool import get_random


def get_text(
     text: str,
     width: float = "auto",
     height: float = "auto",
     cover_pos_label: bool = True,
     color: tuple[str, str] = ("#FFFF00", "#FF7F00"),
     dominant_by_height: bool = True
):
    return _get_text(
        text=text,
        width=width,
        height=height,
        cover_pos_label=cover_pos_label,
        color=color,
        dominant_by_height=dominant_by_height
    )


class Rule3P(AbstractMinesClueRule):
    name = ["3"]
    doc = "雷指向的方向存在n个雷(不包括自己)"

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        random = get_random()
        for pos, _ in board("F"):
            choise = int(random.random() * 4)
            line = []
            match choise:
                case 0:
                    line = board.get_row_pos(pos)
                    line = line[1 + line.index(pos):]
                case 1:
                    line = board.get_row_pos(pos)
                    line = line[:line.index(pos)]
                case 2:
                    line = board.get_col_pos(pos)
                    line = line[1 + line.index(pos):]
                case 3:
                    line = board.get_col_pos(pos)
                    line = line[:line.index(pos)]

            value = board.batch(line, mode="type").count("F")
            obj = Value3P(pos, bytes([value | choise << 6]))
            board.set_value(pos, obj)
        return board


class Value3P(AbstractMinesValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = None):
        self.dir = code[0] >> 6
        self.pos = pos
        self.value = code[0] & 0x3f

    def __repr__(self):
        return "><V^"[self.dir] + str(self.value)

    def web_component(self, board: 'AbstractBoard') -> Dict:
        if self.dir in [0, 1]:
            return get_col(
                get_text("→←↓↑"[self.dir]),
                get_text(str(self.value))
            )
        else:
            return get_row(
                get_text("→←↓↑"[self.dir]),
                get_text(str(self.value))
            )

    def compose(self, board) -> Dict:
        match self.dir:
            case 3:
                # 上 ↑ ^
                if self.value == 1:
                    return get_row(
                            get_dummy(width=0.175),
                            get_text("1"),
                            get_image("up_flag"),
                            get_dummy(width=0.175),
                        )
                return get_row(
                        get_text(str(self.value)),
                        get_image("up_flag"),
                        spacing=-0.1,
                    )
            case 0:
                # 右 → >
                return get_col(
                    get_dummy(height=0.1),
                    get_image(
                        "right_flag",
                        image_height=0.2,
                        image_width=0.7
                    ),
                    get_dummy(height=-0.05),
                    get_text(str(self.value)),
                    get_dummy(height=0.2)
                )
            case 2:
                # 下 ↓ V
                if self.value == 1:
                    return get_row(
                            get_dummy(width=0.175),
                            get_text("1"),
                            get_image("down_flag"),
                            get_dummy(width=0.175),
                        )
                return get_row(
                        get_text(str(self.value)),
                        get_image("down_flag"),
                        spacing=-0.1,
                    )
            case 1:
                # 左 ← <
                return get_col(
                    get_dummy(height=0.1),
                    get_image(
                        "left_flag",
                        image_height=0.2,
                        image_width=0.7
                    ),
                    get_dummy(height=-0.05),
                    get_text(str(self.value)),
                    get_dummy(height=0.2)
                )
        return get_text("")

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        line = []
        match self.dir:
            case 0:
                line = board.get_row_pos(self.pos)
                line = line[1 + line.index(self.pos):]
            case 1:
                line = board.get_row_pos(self.pos)
                line = line[:line.index(self.pos)]
            case 2:
                line = board.get_col_pos(self.pos)
                line = line[1 + line.index(self.pos):]
            case 3:
                line = board.get_col_pos(self.pos)
                line = line[:line.index(self.pos)]
        var_list = board.batch(line, mode="variable")
        model.Add(sum(var_list) == self.value).OnlyEnforceIf(s)

    @classmethod
    def type(cls) -> bytes:
        return Rule3P.name[0].encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value | self.dir << 6])
