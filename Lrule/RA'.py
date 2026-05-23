"""
[RA'] 图书管理员：图书馆，但是所有雷的雷值被打乱了，你需要自己还原。

语义：在完整答案板上，按 `RA` 规则计算每个雷的原始雷值（行内从左到该格的雷数），
然后对这些值做随机置换并作为显示值（special='RA\''）。求解时需要恢复一个将原值映射到显示值的双射映射，同时保证映射与每个格的原始计数一致。

实现说明：
- onboard_init: 在已知完整答案板时构造一个随机置换（仅对题板上出现的原始值进行置换），并注册 special 类型 'RA\'' 返回置换后的显示值。
- create_constraints: 对每个格重建原始计数（与 RA 相同），引入映射布尔变量 `map_o_l` 描述原始值 o 映射到标签 l（1..max_len）的双射关系，并约束当格原始值为 o 且 map_o_l 为真时，显示变量等于 l；非雷时显示为 0。
"""

from typing import Dict, List
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard, AbstractPosition
from minesweepervariants.impl.summon.solver import Switch
from ortools.sat.python import cp_model
import random


class RuleRAp(AbstractMinesRule):
    id = "RA'"
    name = "LibraryPrime"
    name.zh_CN = "图书管理员"
    doc = "Library with scrambled mine-values; solver must restore mapping"
    doc.zh_CN = "图书管理员：图书馆，但是所有雷的雷值被打乱了，你需要自己还原。"
    tags = ["Creative", "Local", "Mine-Value"]
    creation_time = "2026-05-24"
    lib_only = True
    author = ("NT", 2201963934)

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        self.onboard_init(board)
        self.rule = data or "raw"

    def onboard_init(self, board: 'AbstractBoard'):
        # Compute original RA values on the full board and build a random permutation
        # mapping only among values that actually appear.
        def get_type(board: 'AbstractBoard', pos: 'AbstractPosition', *args, **kwargs):
            # Compute original RA value (same as RA): number of mines in this row from left to pos (inclusive)
            raw = board.get_type(pos, special=self.rule)
            if self.rule == 'raw':
                is_mine = int(raw == 'F')
            else:
                is_mine = int(raw)
            if is_mine == 0:
                return 0

            row = board.get_row_pos(pos)
            try:
                idx = row.index(pos)
            except ValueError:
                idx = 0
            count = 0
            for p in row[: idx + 1]:
                p_raw = board.get_type(p, special=self.rule)
                if self.rule == 'raw':
                    p_is_mine = int(p_raw == 'F')
                else:
                    p_is_mine = int(p_raw)
                if p_is_mine == 1:
                    count += 1
            # We'll lazily build a permutation per-board; store on board._meta to reuse
            meta = getattr(board, "_rule_meta", None)
            if meta is None:
                meta = {}
                setattr(board, "_rule_meta", meta)

            key = "RAp_perm"
            if key not in meta:
                # collect present values
                present = []
                for _pos, _ in board(mode="object"):
                    rv = board.get_type(_pos, special=self.rule)
                    if self.rule == 'raw':
                        mine_flag = int(rv == 'F')
                    else:
                        mine_flag = int(rv)
                    if mine_flag == 1:
                        row2 = board.get_row_pos(_pos)
                        try:
                            idx2 = row2.index(_pos)
                        except ValueError:
                            idx2 = 0
                        cnt = 0
                        for p2 in row2[: idx2 + 1]:
                            pr = board.get_type(p2, special=self.rule)
                            if self.rule == 'raw':
                                pr_flag = int(pr == 'F')
                            else:
                                pr_flag = int(pr)
                            if pr_flag == 1:
                                cnt += 1
                        present.append(cnt)
                unique = sorted(set(present))
                perm = unique[:]
                random.shuffle(perm)
                mapping = {o: l for o, l in zip(unique, perm)}
                meta[key] = mapping

            mapping: Dict[int, int] = meta[key]
            return mapping.get(count, count)

        board.register_type_special("RA'", get_type)

    def create_constraints(self, board: 'AbstractBoard', switch: 'Switch') -> None:
        model = board.get_model()
        s = switch.get(model, self)

        # Max possible value equals row length (worst case all left cells are mines)
        max_len = 0
        for key in board.get_interactive_keys():
            for pos, _ in board(key=key):
                max_len = max(max_len, len(board.get_row_pos(pos)))

        if max_len <= 0:
            return

        # Mapping variables: map_o_l == 1 iff original value o maps to label l
        map_vars: Dict[int, Dict[int, cp_model.IntVar]] = {}
        for o in range(1, max_len + 1):
            map_vars[o] = {}
            for l in range(1, max_len + 1):
                map_vars[o][l] = model.NewBoolVar(f"RAp_map_{o}_{l}")

        # bijection constraints across 1..max_len
        for o in range(1, max_len + 1):
            model.Add(sum(map_vars[o][l] for l in range(1, max_len + 1)) == 1)
        for l in range(1, max_len + 1):
            model.Add(sum(map_vars[o][l] for o in range(1, max_len + 1)) == 1)

        # For each position, rebuild original RA count (group_size) and link to displayed value
        for key in board.get_interactive_keys():
            for pos, _ in board(key=key):
                mine = board.get_variable(pos, special="raw")
                det_prime = board.get_variable(pos, special="RA'")

                # Build consecutive contrib booleans for left-to-pos segment
                row = board.get_row_pos(pos)
                try:
                    idx = row.index(pos)
                except ValueError:
                    idx = 0
                left = row[: idx + 1]
                consecutive = []
                for p in left:
                    mv = board.get_variable(p, special="raw")
                    contrib = model.NewBoolVar(f"RAp_contrib_{pos}_{p}")
                    model.Add(contrib <= mv)
                    model.Add(contrib <= mine)
                    consecutive.append(contrib)

                group_size = model.NewIntVar(0, len(consecutive), f"RAp_size_{pos}")
                model.Add(group_size == sum(consecutive))

                # Create indicators orig_eq_o for o in 0..max_len
                for o in range(0, max_len + 1):
                    flag = model.NewBoolVar(f"RAp_eq_{pos}_{o}")
                    model.Add(group_size == o).OnlyEnforceIf(flag)
                    model.Add(group_size != o).OnlyEnforceIf(flag.Not())
                    if o == 0:
                        # non-mine positions should have det_prime == 0
                        model.Add(det_prime == 0).OnlyEnforceIf(flag)
                    else:
                        # link mapping: when group_size==o and map_o_l true then det_prime == l
                        for l in range(1, max_len + 1):
                            model.Add(det_prime == l).OnlyEnforceIf([flag, map_vars[o][l], mine])

                # enforce det_prime == 0 when not mine
                model.Add(det_prime == 0).OnlyEnforceIf(mine.Not())

    def get_deps(self) -> List[str]:
        # depends on raw
        if self.rule == 'raw':
            return []
        return [self.rule]
