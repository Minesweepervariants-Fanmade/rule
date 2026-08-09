#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/08/09
# @Author  : 未知 (740652480)
# @FileName: dlss.py
"""
[dlss] 為14mv啟用dlss，並實現4k全景光追
"""

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board


class RuleDLSS(AbstractMinesRule):
    id = "dlss"
    name = "DLSS"
    name.zh_CN = "DLSS"
    doc = "Enable DLSS for 14mv and implement 4K ray tracing"
    doc.zh_CN = "為14mv啟用dlss，並實現4k全景光追"
    author = ("未知", 740652480)
    tags = ["Creative", "Fun", "WIP"]
    creation_time = "2026-08-09"

    def create_constraints(self, board: 'Board', switch):
        # 此规则不添加任何约束，仅作为占位
        pass
