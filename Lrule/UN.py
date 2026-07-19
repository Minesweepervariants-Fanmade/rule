# -*- coding: utf-8 -*-
"""
[UN] 左线规则 - 隐藏规则

规则描述：
    每个 2x2 子矩阵中的雷数均为偶数。
    当传入任何非 None 的 data 参数时，抛出异常并明确揭示规则内容。

作者: 雾 (3140864122)
最后编辑时间: 2026-07-20 01:00:31
"""

from typing import Optional, Any

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.position import Position


class UN(AbstractMinesRule):
    """
    隐藏左线规则 - 每个 2x2 子矩阵中的雷数均为偶数。
    """

    id = "UN"

    def __init__(self, board=None, data=None):
        """初始化规则，存储 data 参数。"""
        self.data = data
        # 父类 AbstractMinesRule 可能只接受 data 参数
        # 但为了兼容，我们传递 data
        super().__init__(data)
    aliases = ("Even2x2",)
    name = "HiddenEven"
    name.zh_CN = "隐藏偶数"
    doc = "Every 2x2 submatrix contains an even number of mines."
    doc.zh_CN = "每个2x2子矩阵中的雷数均为偶数。"
    author = ("雾", 3140864122)
    tags = ["Local", "Strict Shape"]
    creation_time = "2026-07-20"

    @classmethod
    def get_info(cls) -> dict:
        """返回规则的元信息，隐藏具体规则描述（仅提示）。"""
        info = super().get_info()
        # 覆盖 doc 为隐藏提示，但不改变类属性 doc
        info["doc"] = {
            "zh": (
                "隐藏规则，请通过出题/猜测来发现其具体约束。\n"
                "（提示：这是一个局部偶数约束）"
            ),
            "en": (
                "Hidden rule. Discover the specific constraint "
                "through puzzles/guessing. (Hint: local even constraint)"
            ),
        }
        return info

    def create_constraints(self, board: 'Board', switch) -> None:
        """
        向 CP-SAT 模型添加约束。

        如果 self.data 不为 None，则抛出 ValueError 并揭示规则内容。
        否则，添加约束：每个 2x2 子矩阵中的雷数均为偶数。
        """
        # 当传入非 None 的 data 时，揭示规则
        if self.data is not None:
            raise ValueError(
                "规则 [UN] 的具体内容如下：\n"
                "每个 2x2 子矩阵中的雷数均为偶数。\n"
                "（即任意相邻两行两列构成的 2x2 区域内，雷的数量之和为偶数。）\n"
                f"你传入的数据参数为: {self.data!r}"
            )

        model = board.get_model()
        # 获取开关变量（用于可以禁用该规则，但这里我们总是启用）
        s = switch.get(model, self)

        # 遍历所有位置，以每个位置作为 2x2 子矩阵的左上角
        for pos, _ in board():
            # 检查右、下、右下三个位置是否有效
            pos_r = pos.right()
            pos_d = pos.down()
            pos_rd = pos_r.down()  # 或 pos.down().right()
            if (board.is_valid(pos_r) and board.is_valid(pos_d) and board.is_valid(pos_rd)):
                # 四个位置：pos, pos_r, pos_d, pos_rd
                var_sum = (board.get_variable(pos) + board.get_variable(pos_r) +
                           board.get_variable(pos_d) + board.get_variable(pos_rd))
                # 使用开关变量控制该约束是否生效（默认生效）
                model.AddModuloEquality(0, var_sum, 2).OnlyEnforceIf([s])

    def suggest_total(self, info: dict) -> None:
        """
        建议雷总数范围，该规则不对雷总数做硬性限制。
        但为了确保有解，我们添加一个软约束：总雷数约为格子数的40%~50%。
        """
        # 计算总格子数
        total_cells = 0
        for key in info["interactive"]:
            total_cells += info["total"][key]

        # 如果总格子数>0，建议雷数在0.2~0.6之间，但这是软约束
        if total_cells > 0:
            # 软约束：总雷数在0.2*total_cells 到 0.6*total_cells 之间
            # 使用 soft_fn 添加软约束，权重较低
            info["soft_fn"](total_cells * 0.4, 0)  # 目标值
            # 也可以添加硬约束下界和上界，但这里我们只添加软约束
            # 为了更可靠，添加硬约束：至少1个雷，最多 total_cells-1
            def hard_lower(model, total):
                model.Add(total >= 1)
            def hard_upper(model, total):
                model.Add(total <= total_cells - 1)
            info["hard_fns"].append(hard_lower)
            info["hard_fns"].append(hard_upper)
        else:
            # 没有格子，总雷数只能为0
            def hard_zero(model, total):
                model.Add(total == 0)
            info["hard_fns"].append(hard_zero)
