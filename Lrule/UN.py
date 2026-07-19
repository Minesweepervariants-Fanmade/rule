# -*- coding: utf-8 -*-
"""
[UN] 左线规则 - 隐藏规则

规则描述：
    每个 2x2 子矩阵中的雷数均为奇数。
    当传入任何非 None 的 data 参数时，抛出异常并明确揭示规则内容。

作者: 雾 (3140864122)
最后编辑时间: 2026-07-20 19:20:00

测试方法：
    使用以下命令测试规则是否可以正常生成题目（推荐 5x5 尺寸）：
    D:/python3.13t/python -m minesweepervariants -a 1 --onseed -t -1 -s 5 5 -c UN

    如果需要测试传入 data 参数时是否抛出异常：
    D:/python3.13t/python -m minesweepervariants -a 1 --onseed -t -1 -s 5 5 -c UN:test
    此时应抛出 ValueError 并揭示规则内容。
"""

from typing import Optional, Any

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.position import Position


class UN(AbstractMinesRule):
    """
    隐藏左线规则 - 每个 2x2 子矩阵中的雷数均为奇数。
    """

    id = "UN"

    def __init__(self, board=None, data=None):
        """初始化规则，存储 data 参数。"""
        # 如果 data 不为 None，立即揭示规则
        if data is not None:
            raise ValueError(
                "规则 [UN] 的具体内容如下：\n"
                "每个 2x2 子矩阵中的雷数均为奇数。\n"
                "（即任意相邻两行两列构成的 2x2 区域内，雷的数量之和为偶数。）\n"
                f"你传入的数据参数为: {data!r}"
            )
        self.data = data
        super().__init__(data)

    aliases = ("Even2x2",)
    name = "未知"
    name.zh_CN = "未知"
    doc = "未知"
    doc.zh_CN = "未知"
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
                "（提示：这是一个局部偶数约束，作用范围为2x2）"
            ),
            "en": (
                "Hidden rule. Discover the specific constraint "
                "through puzzles/guessing. (Hint: local even constraint, 2x2 scope)"
            ),
        }
        return info

    def create_constraints(self, board: 'Board', switch) -> None:
        """
        向 CP-SAT 模型添加约束。

        添加约束：每个 2x2 子矩阵中的雷数均为奇数。
        """
        model = board.get_model()
        # 获取开关变量（用于可以禁用该规则，但这里我们总是启用）
        s = switch.get(model, self)

        # 遍历所有位置，以每个位置作为 2x2 子矩阵的左上角
        for pos, _ in board():
            # 检查右、下、右下三个位置是否有效
            pos_r = pos.right()
            pos_d = pos.down()
            pos_rd = pos_r.down() if pos_r else None

            # 如果这三个位置都有效，则构成一个完整的 2x2 子矩阵
            if (board.is_valid(pos_r) and board.is_valid(pos_d) and board.is_valid(pos_rd)):
                # 四个位置：pos, pos_r, pos_d, pos_rd
                var_sum = (board.get_variable(pos) +
                           board.get_variable(pos_r) +
                           board.get_variable(pos_d) +
                           board.get_variable(pos_rd))
                # 要求雷数之和为偶数：即模2余0
                # 使用 AddModuloEquality 约束
                model.AddModuloEquality(0, var_sum, 2).OnlyEnforceIf([s])

    def suggest_total(self, info: dict) -> None:
        """
        建议雷总数范围，该规则不对雷总数做硬性限制。
        但为了确保有解，添加软约束和基本的硬约束。
        """
        # 计算总格子数
        total_cells = 0
        for key in info["interactive"]:
            total_cells += info["total"][key]

        if total_cells > 0:
            # 软约束：总雷数在0.2~0.6之间
            info["soft_fn"](total_cells * 0.4, 0)  # 目标值
            # 硬约束：至少1个雷，最多 total_cells-1
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
