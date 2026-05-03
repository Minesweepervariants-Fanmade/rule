#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/08/23 23:52
# @Author  : Wu_RH
# @FileName: Fshape.py

from minesweepervariants.abs.board import AbstractBoard
from . import AbstractMinesSharp


class RuleFsharp(AbstractMinesSharp):
    id = "F#"
    name = "Mineclue Label"
    name.zh_CN = "雷线索标签"
    doc = "Contains the following rules: [*3T], [3], [3F]"
    doc.zh_CN = "包含以下规则: [*3T], [3], [3F]"
    tags = ["Original", "Local", "Extensive trial"]

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        rules_name = ["*3T", "3", "3F"]
        super().__init__(rules_name, board, data)
