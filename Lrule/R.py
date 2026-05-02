#!/usr/bin/env python3
# -*- coding:utf-8 -*-

# @Time    : 2025/06/03 18:59
# @Author  : Wu_RH
# @FileName: R0.py

"""
[R]总雷数: 题板内的雷数量为一个整数
"""

from ....abs.Lrule import Rule0R


class RuleR(Rule0R):
    id = "R"
    name = "Total Mines"
    name.zh_CN = "总雷数"
    doc = "Sometimes you need total mine count to deduce"
    doc.zh_CN = "有时你会需要用到总雷数来推理"
