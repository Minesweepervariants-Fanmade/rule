#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/01/11 10:04
# @Author  : Wu_RH
# @FileName: Bingo.py

from ...impl_obj import get_rule
from ...summon.solver import Switch
from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard
from ....config.config import PUZZLE_CONFIG
from ....utils.tool import get_logger, get_random

main_rules = ["1Q", "1C", "1T", "1O", "1D", "1B", "2C", "2G", "2G'", "2H", "2B", "2T"]

CONFIG = {}
CONFIG.update(PUZZLE_CONFIG)


class BINGO(AbstractMinesRule):
    name = ["4B", "宾果", "Bingo"]
    doc = "每个格子被随机标记一个左线规则。当该格为雷时，完整题板必须满足该格的规则。"

    def __init__(self, board: AbstractBoard, data=None):
        super().__init__(board, data)
        random = get_random()
        positions = []
        for key in board.get_interactive_keys():
            board.set_config(key, "pos_label", True)
            positions.extend([pos for pos, _ in board(key=key)])
        rule_list = [''] if data else main_rules
        data = "" if data is None else data
        tagRate, data = data.split(";") if (";" in data) else (50, data)
        tagRate = int(tagRate)
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
        if rule_list[-1] == "":
            rule_list.pop(-1)
        if len(rule_list) == 0:
            rule_list = main_rules
        if "ALL" in rule_list:
            rule_list.remove("ALL")
            for rule_class in AbstractMinesRule.__subclasses__():
                if rule_class.name[0] in [
                    "HYW", "OR", "AND", "", "0", "3E", "2I1C", "SETU", "4B",
                    "1N", "1M", "3D", "3I", "4S''", "4S'", "4S", "SCREAM", "3U"
                ]:
                    continue
                rule_list.append(rule_class.name[0])
        get_logger().info(f"Init 4B with rules {rule_list}")
        self.rules = []
        for rule in rule_list:
            if CONFIG["delimiter"] in rule:
                rule_name, rule_data = rule.split(CONFIG["delimiter"], 1)
            else:
                rule_name = rule
                rule_data = None
            try:
                rule = get_rule(rule_name)(board=board, data=rule_data)
            except Exception as e:
                get_logger().warn(f"Error in rule [{rule_name}]: {e}")
                continue
            if not isinstance(rule, AbstractMinesRule):
                continue
            self.rules.append(rule)
        positions = random.sample(positions, len(positions) * tagRate // 100)
        get_logger().info(f"Init 4B choose positions {positions}")
        self.label_dict = {}
        _rules = []
        for pos in positions:
            if not _rules:
                _rules = self.rules.copy()
                random.shuffle(_rules)
            self.label_dict[pos] = _rules.pop()
        _label_dict = {pos: self.label_dict[pos].get_name() for pos in self.label_dict}
        for key in board.get_interactive_keys():
            board.set_config(key, "labels", _label_dict)
        get_logger().info(f"Init 4B label_dict {_label_dict}")

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        model = board.get_model()
        switch_map = {}

        for pos, rule in self.label_dict.items():
            if rule in switch_map:
                switch_map[rule].append(board.get_variable(pos))
            else:
                switch_map[rule] = [board.get_variable(pos)]

        for rule in set(self.label_dict.values()):
            bool_var = model.NewBoolVar(f"switch[{rule.get_name()}]")
            rule.create_constraints(board, FakeSwitch(bool_var))
            get_logger().trace(f"4B: {rule.get_name()} create constraints")
            for switch_pos_var in switch_map[rule]:
                model.Add(bool_var == 1).OnlyEnforceIf(switch_pos_var)


class FakeSwitch(Switch):
    def __init__(self, var) -> None:
        self.var = var
        super().__init__()

    def get(self, model, obj, index=None):
        return self.var
