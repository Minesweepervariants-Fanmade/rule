#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/11 14:25
# @Author  : xxx
# @FileName: 1D.py
"""
[HYW]何意味
"""

from ....abs.Lrule import AbstractMinesRule

class 何意味(Exception):
    pass

class Rule1D(AbstractMinesRule):
    id = "HYW"
    name = "??"
    name.zh_CN = "何意味"
    doc = "\"What does it mean?\""
    doc.zh_CN = "何意味"
    author = ("NT", 2201963934)


    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        raise 何意味("何意味")