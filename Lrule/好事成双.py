#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/11/21 01:27:31
# @Author  : NT (2201963934)
# @FileName: 好事成双.py
"""
[好事成双] 行/列中最长的连续雷组恰好有两个

规则拆分定义(验收基准):
1. 规则对象与适用范围:
   - 左线规则 (Lrule, AbstractMinesRule)，约束每个可交互题板 (board.get_interactive_keys()) 的原始雷布局 (special='raw')，无 fill 阶段。
2. 核心术语精确定义:
   - 行内连续雷组: 在同一行中沿水平方向极大连续的雷格序列 (长度 >= 1)，遇到非雷格、边界或无效格(mask)截断。
   - 列内连续雷组: 在同一列中沿竖直方向极大连续的雷格序列 (长度 >= 1)，遇到非雷格、边界或无效格(mask)截断。
   - 合并统计集合 G: 将全盘所有行内连续雷组与所有列内连续雷组按格点集合合并 (行与列不分开统计)。
     - 长度 L >= 2 时，任意水平连续雷组与任意竖直连续雷组对应的格点集合均不相同(相交至多 1 格，如 L/T/+ 形计为 2 组)。
     - 长度 L == 1 时，孤立单雷在行和列中对应同一单格集合 {(r, c)}，合并后仅计 1 组(不重复计数)。
   - 最长连续雷组恰好有两个: G 非空，令 L_max = max_{g in G} |g| >= 1，则满足 |g| == L_max 的雷组数量恰好为 2。
3. 边界条件与越界处理:
   - 全空题板 (0 雷) 时 G 为空，不满足规则。
   - 若 L_max == 1，则全盘不能有相邻雷(无长度 >= 2 的连续雷组)，且全盘恰好有 2 个孤立单雷。
   - 若棋盘无法容纳任意长度的 2 个连续雷组(如 1x1 棋盘)，规则在激活时不可满足。
4. create_constraints 充要等价建模:
   - 对每个长度 L >= 2，构造所有水平/竖直长度为 L 的连续窗口全雷指示变量 W_L；对 L == 1，W_1 为所有有效格的雷变量列表(每格计一次)。
   - 对任意可行长度 L (|W_L| >= 2)，L_max == L 且最长连续雷组恰有 2 个，充要等价于:
     (a) sum(W_L) == 2；且
     (b) 若 W_{L+1} 非空，则 W_{L+1} 中所有变量均为 0 (无长度 >= L+1 的连续雷，从而 W_L 中为 1 的窗口与极大连续雷组一一对应)。
   - 通过互斥选择变量 is_max[L] 要求恰有一个可行 L 成立，并由 switch.get(model, self) 条件化。
5. 可验证样例:
   - 样例A(满足, L_max=3): 5x5 盘面有 1 个水平 3 连雷和 1 个竖直 3 连雷，其余雷连长 <= 2 -> 最长长度 3，共 2 组，合法。
   - 样例B(满足, L_max=2): 2x2 盘面呈 L 形 3 雷 {(0,0),(0,1),(1,0)} -> 水平 2 连 1 组 + 竖直 2 连 1 组，共 2 组，合法。
   - 样例C(不满足): 2x2 全雷 -> 水平 2 连 2 组 + 竖直 2 连 2 组 = 4 组 != 2，非法。
   - 样例D(满足, L_max=1): 5x5 盘面仅有 2 个互不四连通相邻的孤立雷 -> L_max=1，共 2 组，合法；若仅 1 个雷则仅 1 组，非法。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ortools.sat.python.cp_model import IntVar

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board

if TYPE_CHECKING:
    from minesweepervariants.impl.summon.solver import Switch


class RuleHSCS(AbstractMinesRule):
    """[好事成双] 行/列中最长的连续雷组恰好有两个"""

    id = "好事成双"
    name = "Good Things Come in Pairs"
    name.zh_CN = "好事成双"
    doc = "Across all rows and columns combined, there are exactly two longest consecutive mine groups"
    doc.zh_CN = "行/列中最长的连续雷组恰好有两个"
    author = ("NT", 2201963934)
    tags = ["Original", "Global", "Construction"]
    creation_time = "2026-11-21"

    def __init__(self, board: "Board | None" = None, data: str | None = None) -> None:
        super().__init__(board, data)

    @staticmethod
    def _collect_segments(
        board: Board, key: str
    ) -> tuple[list[IntVar], list[list[IntVar]], list[list[IntVar]]]:
        """收集当前题板所有有效格变量，以及按行/列切分的极大连续有效格段。"""
        size = board.get_config(key, "size")
        if size is None:
            return [], [], []

        rows, cols = size.rows, size.cols
        cell_vars: list[IntVar] = []
        row_segs: list[list[IntVar]] = []
        col_segs: list[list[IntVar]] = []

        for r in range(rows):
            seg: list[IntVar] = []
            for c in range(cols):
                pos = board.get_pos(r, c, key)
                var = board.get_variable(pos, special="raw") if pos is not None else None
                if var is not None:
                    cell_vars.append(var)
                    seg.append(var)
                elif seg:
                    row_segs.append(seg)
                    seg = []
            if seg:
                row_segs.append(seg)

        for c in range(cols):
            seg = []
            for r in range(rows):
                pos = board.get_pos(r, c, key)
                var = board.get_variable(pos, special="raw") if pos is not None else None
                if var is not None:
                    seg.append(var)
                elif seg:
                    col_segs.append(seg)
                    seg = []
            if seg:
                col_segs.append(seg)

        return cell_vars, row_segs, col_segs

    def create_constraints(self, board: Board, switch: "Switch") -> None:
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            cell_vars, row_segs, col_segs = self._collect_segments(board, key)
            if len(cell_vars) < 2:
                model.add(0 == 1).only_enforce_if(s)
                continue

            windows_by_len: dict[int, list[IntVar]] = {1: cell_vars}

            # 递推构造所有长度 L >= 2 的水平与竖直连续窗口全雷指示变量
            for axis_tag, segs in (("r", row_segs), ("c", col_segs)):
                for seg_idx, seg in enumerate(segs):
                    seg_len = len(seg)
                    if seg_len < 2:
                        continue
                    prev_layer: list[IntVar] = seg
                    for length in range(2, seg_len + 1):
                        cur_layer: list[IntVar] = []
                        win_bucket = windows_by_len.setdefault(length, [])
                        for start in range(seg_len - length + 1):
                            prev_var = prev_layer[start]
                            tail_var = seg[start + length - 1]
                            win_var = model.new_bool_var(
                                f"hscs_{key}_{axis_tag}{seg_idx}_l{length}_s{start}"
                            )
                            model.add_bool_and([prev_var, tail_var]).only_enforce_if(win_var)
                            model.add_bool_or([prev_var.Not(), tail_var.Not(), win_var])
                            cur_layer.append(win_var)
                            win_bucket.append(win_var)
                        prev_layer = cur_layer

            possible_lengths = [
                length
                for length in sorted(windows_by_len)
                if len(windows_by_len[length]) >= 2
            ]
            if not possible_lengths:
                model.add(0 == 1).only_enforce_if(s)
                continue

            choice_vars: list[IntVar] = []
            for length in possible_lengths:
                is_max = model.new_bool_var(f"hscs_{key}_max_{length}")
                choice_vars.append(is_max)

                # 当最长长度为 length 时: 长度 length 的窗口恰有 2 个全雷
                model.add(sum(windows_by_len[length]) == 2).only_enforce_if([is_max, s])

                # 且不存在任意长度为 length + 1 的全雷窗口(自动禁止所有 > length 的连续雷)
                longer_windows = windows_by_len.get(length + 1)
                if longer_windows:
                    model.add_bool_and([w.Not() for w in longer_windows]).only_enforce_if(
                        [is_max, s]
                    )

            model.add(sum(choice_vars) == 1).only_enforce_if(s)
