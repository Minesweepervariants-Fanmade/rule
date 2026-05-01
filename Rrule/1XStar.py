#!/usr/bin/env python3

"""
[1X*] 王后 (Queen)：线索数表示斜向和横纵所有格子中的雷数
"""
from .CQ import Rule1XStar as AbstractClueRule


class Rule1XStar(AbstractClueRule):
    id = "1X*"
    name = "Queen"
    name.zh_CN = "王后"
    doc = "线索数表示斜向和横纵所有格子中的雷数"
