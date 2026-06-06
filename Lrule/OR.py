#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/08/08 12:15
# @Author  : Wu_RH
# @FileName: OR.py
"""
[OR]或:你可以在后面输入多个左线来表示或关系(题板将按照A规则或B规则)(规则间使用":"隔开)
"""
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.config.config import PUZZLE_CONFIG

from ...impl_obj import get_rule
from ...summon.solver import Switch

CONFIG = {}
CONFIG.update(PUZZLE_CONFIG)


class RuleOR(AbstractMinesRule):
    id = "OR"
    name = "OR"
    name.zh_CN = "或"
    doc = "You can input multiple left rules separated by ':' to express OR relationship (board will follow either rule A or rule B)"
    doc.zh_CN = "你可以在后面输入多个左线来表示或关系(题板将按照A规则或B规则)(规则间使用\":\"隔开)"
    tags = ["Meta", "Global", "Parameter"]
    creation_time = "2025-08-08"
    author = ("", 0)

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        self.n = 1
        rule_list = [""]
        deep = 0
        for s in data:
            if s == "(":
                if deep > 0:
                    rule_list[-1] += "("
                deep += 1
            elif s == ")":
                if deep > 1:
                    rule_list[-1] += ")"
                deep -= 1
            elif s == ":" and deep == 0:
                rule_list.append("")
            else:
                rule_list[-1] += s
        if len(rule_list) == 0:
            raise ValueError("你不能或空的规则")
        self.rules = []
        if not rule_list[0].isdigit():
            self.n = 1
            rule_list = [None] + rule_list
        else:
            self.n = int(rule_list[0])
        for rule in rule_list[1:]:
            if CONFIG["delimiter"] in rule:
                rule_name, rule_data = rule.split(CONFIG["delimiter"], 1)
            else:
                rule_name = rule
                rule_data = None
            rule = get_rule(rule_name)(board=board, data=rule_data)
            if not isinstance(rule, AbstractMinesRule):
                continue
            self.rules.append(rule)

    def create_constraints(self, board: 'Board', switch: 'Switch'):
        model = board.get_model()
        var_list = []
        for rule in self.rules:
            z = model.new_bool_var("OR")
            _switch = Switch()
            rule.create_constraints(board=board, switch=_switch)
            model.add_bool_and(_switch.get_all_vars()).OnlyEnforceIf(z)
            var_list.append(z)
        model.add(sum(var_list) >= self.n).OnlyEnforceIf(switch.get(model, self))
