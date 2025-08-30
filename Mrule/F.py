#!/usr/bin/env python3
# -*- coding:utf-8 -*-

# @Time    : 2025/06/03 19:00
# @Author  : Wu_RH
# @FileName: F0.py

"""
[F]标准雷线索: 雷线索表示该格是一个雷
"""

from ....abs.Mrule import Rule0F as AbstractRule0F


class RuleF(AbstractRule0F):
    name = ["F", "雷"]
    doc = "线索表示该格是一个非雷"
