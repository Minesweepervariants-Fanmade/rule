#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/07/14 01:41
# @Author  : 雾 (3140864122)
# @FileName: RL1.py
"""
[RL1] 对称数字左线规则

填写完标准扫雷规则数字的题板下，所有相同数字周围的雷分布均相同
（允许旋转90/180/270度与四个旋转情况的x/y镜像对称）

实现：使用模板变量和对称变换，对于每个非雷位置，其周围雷模式必须与某个数字模板在某种对称变换下一致。
"""

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.position import Position


def get_permutations():
    """返回8个对称变换的排列，每个排列是长度为8的列表，表示原始方向索引变换后的方向索引。
    方向顺序：上(0), 右上(1), 右(2), 右下(3), 下(4), 左下(5), 左(6), 左上(7)
    对应的坐标偏移：(-1,0), (-1,1), (0,1), (1,1), (1,0), (1,-1), (0,-1), (-1,-1)
    """
    dirs = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
    # 8种变换函数
    transform_funcs = [
        lambda dr, dc: (dr, dc),                     # 0: 恒等
        lambda dr, dc: (dc, -dr),                    # 1: 顺时针旋转90度
        lambda dr, dc: (-dr, -dc),                   # 2: 旋转180度
        lambda dr, dc: (-dc, dr),                    # 3: 逆时针旋转90度
        lambda dr, dc: (-dr, dc),                    # 4: 水平翻转（左右镜像）
        lambda dr, dc: (dr, -dc),                    # 5: 垂直翻转（上下镜像）
        lambda dr, dc: (dc, dr),                     # 6: 主对角线镜像
        lambda dr, dc: (-dc, -dr),                   # 7: 副对角线镜像
    ]
    perms = []
    for tf in transform_funcs:
        perm = []
        for dr, dc in dirs:
            ndr, ndc = tf(dr, dc)
            # 查找(ndr, ndc)在dirs中的索引
            idx = dirs.index((ndr, ndc))
            perm.append(idx)
        perms.append(perm)
    return perms


PERMS = get_permutations()


class RuleRL1(AbstractMinesRule):
    id = "RL1"
    aliases = ("SL1", "SymmetryLeft1")
    name = "Symmetric Digits"
    name.zh_CN = "对称数字"
    doc = (
        "For all positions with the same digit, the mine pattern around them must be identical "
        "under rotation/reflection symmetry."
    )
    doc.zh_CN = (
        "所有相同数字的位置，其周围的雷分布模式在旋转/镜像对称下必须相同。"
    )
    author = ("雾 (3140864122)", 3140864122)
    tags = ["Original", "Global", "Strict R", "Strong"]
    creation_time = "2026-07-14"

    def create_constraints(self, board: 'Board', switch):
        """
        创建约束：
        对于每个非雷位置，其周围雷数 n 在 1~7 之间时，存在一个数字模板 T_n（8个方向）
        和一个对称变换（共8种），使得该位置的邻居雷变量等于变换后的模板。
        当 n=0 时，邻居全为0；当 n=8 时，邻居全为1。
        """
        model = board.get_model()
        s = switch.get(model, self)

        # 获取所有位置
        positions = [pos for pos, _ in board()]
        if not positions:
            return

        # 创建模板变量 T[d][i] 对于 d=1..7，i=0..7
        T = {}
        for d in range(1, 8):
            T[d] = [model.NewBoolVar(f'T_{d}_{i}') for i in range(8)]

        # 遍历每个位置
        for pos in positions:
            # 获取当前格的雷变量
            mine_var = board.get_variable(pos)
            if mine_var is None:
                continue

            # 收集8个邻居雷变量（边界外视为0）
            dirs = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
            neighbor_vars = []
            for dr, dc in dirs:
                n_pos = Position(pos.col + dc, pos.row + dr, pos.board_key)
                if board.in_bounds(n_pos):
                    var = board.get_variable(n_pos)
                    if var is None:
                        var = model.NewBoolVar(f'dummy_{pos}_{len(neighbor_vars)}')
                        model.Add(var == 0)
                    neighbor_vars.append(var)
                else:
                    var = model.NewBoolVar(f'dummy_{pos}_{len(neighbor_vars)}')
                    model.Add(var == 0)
                    neighbor_vars.append(var)

            # 周围雷数变量 n_pos
            n_pos = sum(neighbor_vars)  # IntVar

            # 选择数字变量 sel_digit[d] for d=0..8
            sel_digit = [model.NewBoolVar(f'sel_{pos}_d{d}') for d in range(9)]
            # 恰好一个数字被选中
            model.Add(sum(sel_digit) == 1).OnlyEnforceIf(s)
            for d in range(9):
                model.Add(n_pos == d).OnlyEnforceIf([sel_digit[d], s])

            # d=0: 全0，但 n_pos==0 已经保证，无需额外约束
            # d=8: 全1，但 n_pos==8 已经保证，无需额外约束

            # d=1..7: 需要选择模板和变换
            # 创建选择变换变量 x[d][k]
            x = {}
            for d in range(1, 8):
                for k in range(8):
                    x[(d, k)] = model.NewBoolVar(f'x_{pos}_{d}_{k}')

            # 对于每个 d，sum_k x[d][k] == sel_digit[d]
            for d in range(1, 8):
                model.Add(sum(x[(d, k)] for k in range(8)) == sel_digit[d]).OnlyEnforceIf(s)

            # 对于每个 d 和 k，如果 x[d][k] 为真，则邻居变量等于变换后的模板
            for d in range(1, 8):
                for k in range(8):
                    perm = PERMS[k]  # 排列列表
                    for i in range(8):
                        # 原始方向 i 经过变换后对应方向 perm[i]
                        # 约束 neighbor_vars[i] == T[d][perm[i]]
                        model.Add(neighbor_vars[i] == T[d][perm[i]]).OnlyEnforceIf([x[(d, k)], s])
