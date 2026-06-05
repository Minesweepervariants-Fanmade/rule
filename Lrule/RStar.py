"""
[R*] 总雷数参数规则: 题板内每个 interactive key 的总雷数必须满足给定比较串。

规则拆分定义(验收基准):
1) 规则对象与适用范围:
    - 左线规则(Lrule)。
    - 约束对象是当前 interactive key 内所有有效格的 raw 状态。
    - 统计对象仅为题板总雷数, 即所有参与建模的 raw=1 之和。

2) 核心术语精确定义:
    - 总雷数: 当前 key 内所有可枚举有效格上 raw=1 的数量。
    - 比较串: 由可选的模前缀和一个比较子句组成, 例如 "=3", ">4", "<5", "!=7", "%3=2", "%20>=3", "%3!=4"。
    - 模前缀 "%n" 表示先计算总雷数对 n 取模, 再对余数做比较。
    - 若不存在模前缀, 则比较对象就是总雷数本身。
    - 允许的比较符号为 =, !=, >, >=, <, <=。

3) 计数对象、边界条件、越界处理:
    - 仅统计 board(key=当前 key) 可枚举到、且 raw 变量非空的有效格。
    - 越界格、洞格、非交互格不参与总雷数。
    - 模数必须为正整数; 若参数写成 "%0..." 或负模数, 视为非法参数。
    - 比较值可以为任意整数; 例如 "%3!=4" 语义上成立为“模 3 后的余数不等于 4”。

4) 参数与约束语义:
    - data 为 None 或空字符串时, 默认行为等价于 "=3"。
    - data 为单个比较串时, 直接按一个约束解释。
    - 参数只限制总雷数, 不改变布雷、线索生成或任何其他规则语义。
    - create_constraints 阶段必须与参数语义逐字等价; 不得只编码成近似上界/下界。

5) fill 阶段语义与 create_constraints 阶段语义的等价关系:
    - 该规则属于左线全局约束, 不负责 fill。
    - create_constraints 只需把当前盘面的 raw 总和与参数条件做等价约束。
    - 若后续被组合进更高层规则, 其语义仍然只约束总雷数。

6) 可验证样例:
    - 样例A: 一个 5x5 盘面总雷数为 12, 参数 "=12" 应通过。
    - 样例B: 一个 5x5 盘面总雷数为 14, 参数 "%3=2" 应通过, 因为 14 % 3 = 2。
    - 样例C: 一个 5x5 盘面总雷数为 14, 参数 "%20>=3" 应通过, 因为 14 % 20 = 14。
    - 样例D: 一个 5x5 盘面总雷数为 7, 参数 "!=7" 应失败。

作者: NT
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, List, Tuple

from ....abs.Lrule import AbstractMinesRule

if TYPE_CHECKING:
    from ....abs.board import AbstractBoard
    from ....impl.summon.solver import Switch


_COMPARE_RE = re.compile(r"^(?:%(?P<mod>-?\d+))?(?P<op>=|!=|>=|<=|>|<|~=)(?P<value>-?\d+)$")


def _parse_single_comparison(text: str) -> Tuple[int | None, str, int]:
    """解析单个比较串，返回 (modulus, operator, target)"""
    match = _COMPARE_RE.fullmatch(text)
    if match is None:
        raise ValueError(f"非法参数: {text!r}")

    modulus_text = match.group("mod")
    modulus = None if modulus_text is None else int(modulus_text)
    if modulus is not None and modulus <= 0:
        raise ValueError("模数必须为正整数")

    return modulus, match.group("op"), int(match.group("value"))


def _parse_comparisons(data) -> List[Tuple[int | None, str, int]]:
    """解析由分号分隔的多个比较串，返回列表"""
    if data is None:
        data = ""
    raw = "".join(str(data).split())
    if not raw:
        # 默认约束 "=3"
        return [(None, "=", 3)]

    parts = raw.split(";")
    constraints = []
    for part in parts:
        if not part:
            continue
        constraints.append(_parse_single_comparison(part))
    if not constraints:
        # 如果只有空串（例如 ";"），回退到默认
        return [(None, "=", 3)]
    return constraints


class RuleRStar(AbstractMinesRule):
    id = "R*"
    name = "R*"
    name.zh_CN = "R*"
    doc = "For each interactive key, the total number of mines must satisfy the given comparison string."
    doc.zh_CN = "对每个 interactive key, 其总雷数必须满足给定比较串"
    author = ("NT", 2201963934)
    tags = ["Global", "Strict R", "Parameter", "Original"]
    creation_time = "2026-05-24"

    def __init__(self, board: 'AbstractBoard' = None, data=None) -> None:
        super().__init__(board, data)
        self.constraints = _parse_comparisons(data)

    @staticmethod
    def _apply_comparison(model, lhs, op: str, rhs: int, switch_var) -> None:
        if op == "=":
            model.Add(lhs == rhs).OnlyEnforceIf(switch_var)
        elif op == "!=":
            model.Add(lhs != rhs).OnlyEnforceIf(switch_var)
        elif op == ">":
            model.Add(lhs > rhs).OnlyEnforceIf(switch_var)
        elif op == ">=":
            model.Add(lhs >= rhs).OnlyEnforceIf(switch_var)
        elif op == "<":
            model.Add(lhs < rhs).OnlyEnforceIf(switch_var)
        elif op == "<=":
            model.Add(lhs <= rhs).OnlyEnforceIf(switch_var)
        elif op == "~=":
            pass
        else:
            raise ValueError(f"不支持的比较符号: {op}")

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
        model = board.get_model()
        rule_switch = switch.get(model, self)

        for key in board.get_interactive_keys():
            mine_vars = [
                var
                for _, var in sorted(
                    board(key=key, mode="variable", special="raw"),
                    key=lambda item: (item[0].x, item[0].y),
                )
                if var is not None
            ]

            total_ub = len(mine_vars)
            total_var = model.new_int_var(0, total_ub, f"RStar_total_{key}")
            model.add(total_var == sum(mine_vars)).OnlyEnforceIf(rule_switch)

            # 对每一个约束分别添加条件
            for modulus, operator, target in self.constraints:
                if modulus is None:
                    # 直接比较总雷数
                    self._apply_comparison(model, total_var, operator, target, rule_switch)
                else:
                    # 先取模，再比较余数
                    remainder = model.new_int_var(0, modulus - 1, f"RStar_mod_{key}_{modulus}")
                    quotient = model.new_int_var(0, total_ub // modulus, f"RStar_quo_{key}_{modulus}")
                    model.add(total_var == quotient * modulus + remainder).OnlyEnforceIf(rule_switch)
                    self._apply_comparison(model, remainder, operator, target, rule_switch)

    def suggest_total(self, info) -> None:
        target_value = []
        for _, operator, target in self.constraints:
            if operator == "~=":
                target_value.append(target)
        if target_value:
            info["soft_fn"](int(sum(target_value) / len(target_value)), 5)
