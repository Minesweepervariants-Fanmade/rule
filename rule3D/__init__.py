#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/07/04 10:33
# @Author  : Wu_RH
# @FileName: __init__.py
import heapq
from abc import ABC
from typing import List, Optional

from ....abs.Lrule import AbstractMinesRule
from ....abs.Mrule import AbstractMinesClueRule
from ....abs.Rrule import AbstractClueRule
from ....abs.board import AbstractBoard, AbstractPosition
from ....utils.impl_obj import VALUE_QUESS, MINES_TAG


class Abstract3DRule:
    def __init__(self, board: AbstractBoard, data: str = None):
        if data == "":
            return
        size = (board.boundary().x + 1, board.boundary().y + 1)
        for i in range((min(size) - 1) if data is None else int(data) - 1):
            key = f"{i + 2}"
            board.generate_board(key, size)
            board.set_config(key, "interactive", True)
            board.set_config(key, "row_col", True)
            board.set_config(key, "VALUE", VALUE_QUESS)
            board.set_config(key, "MINES", MINES_TAG)

    @staticmethod
    def pos_index(board: AbstractBoard, pos):
        return board.get_interactive_keys().index(pos.board_key)

    @classmethod
    def down(cls, board: AbstractBoard, pos: AbstractPosition, n=1):
        keys = board.get_interactive_keys()
        if pos.board_key not in keys:
            return None
        pos = pos.clone()
        index = keys.index(pos.board_key) - n
        if -1 < index < len(keys):
            pos.board_key = keys[index]
            return pos
        return None

    @classmethod
    def up(cls, board: AbstractBoard, pos: AbstractPosition, n=1):
        keys = board.get_interactive_keys()
        if pos.board_key not in keys:
            return None
        pos = pos.clone()
        index = keys.index(pos.board_key) + n
        if -1 < index < len(keys):
            pos.board_key = keys[index]
            return pos
        return None

    @staticmethod
    def pos_neighbors(board, pos: AbstractPosition, *args: int) -> List[AbstractPosition]:
        """
        按照欧几里得距离从小到大逐层扩散，筛选范围由距离平方控制（不包含当前位置）。

        调用方式（类似 range）：
            neighbors(end_layer)
                返回所有欧几里得距离 ≤ √end_layer 的位置（从第 1 层开始）。
            neighbors(start_layer, end_layer)
                返回所有欧几里得距离 ∈ [√start_layer, √end_layer] 的位置。

        :param board: 题板对象
        :param pos: 起始位置
        :param args: 一个或两个整数
            - 若提供一个参数 end_layer，视为从 √1 到 √end_layer。
            - 若提供两个参数 start_layer 和 end_layer，视为从 √start_layer 到 √end_layer。
            - 参数非法（数量不为 1 或 2，或值非法）时返回空列表。

        :return: 位置列表，按距离从近到远排序。
        """
        # 解析参数
        if len(args) == 1:
            start_sq = 1
            end_sq = args[0]
        elif len(args) == 2:
            start_sq = args[0]
            end_sq = args[1]
        else:
            return []

        # 检查参数有效性
        if end_sq < start_sq:
            return []

        # 定义移动函数（单位向量移动）
        def move_by_vector(
                _p: AbstractPosition, _dx: int, _dy: int, _dz: int
        ) -> Optional[AbstractPosition]:
            """按向量(dx, dy, dz)移动位置（每步移动1格）"""
            temp = _p

            # x轴移动
            if _dx != 0:
                if _dx > 0:
                    temp = temp.right(n=_dx)
                else:
                    temp = temp.left(n=-_dx)
                if temp is None:
                    return None

            # y轴移动（二维方向）
            if _dy != 0:
                if _dy > 0:
                    temp = temp.down(n=_dy)
                else:
                    temp = temp.up(n=-_dy)
                if temp is None:
                    return None

            # z轴移动（三维方向）
            if _dz != 0:
                if _dz > 0:
                    temp = Abstract3DRule.up(board, temp, n=_dz)
                else:
                    temp = Abstract3DRule.down(board, temp, n=-_dz)
                if temp is None:
                    return None

            return temp

        # 记录起点坐标
        x0, y0, z0 = pos.x, pos.y, Abstract3DRule.pos_index(board, pos)
        result = []

        # 生成26个三维方向向量（排除(0,0,0)）
        directions = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    if dx == 0 and dy == 0 and dz == 0:
                        continue
                    directions.append((dx, dy, dz))

        # 使用最小堆存储（距离平方, 位置）
        heap = []
        visited = set()
        visited.add((x0, y0, z0))  # 标记起点已访问

        # 初始化：加入所有相邻位置
        for dx, dy, dz in directions:
            neighbor = move_by_vector(pos, dx, dy, dz)
            if neighbor is None:
                continue
            n_coord = (neighbor.x, neighbor.y, Abstract3DRule.pos_index(board, neighbor))

            # 避免重复访问
            if n_coord in visited:
                continue
            visited.add(n_coord)

            # 计算欧几里得距离平方
            dist_sq = (neighbor.x - x0) ** 2 + (neighbor.y - y0) ** 2 + (
                        Abstract3DRule.pos_index(board, neighbor) - z0) ** 2
            heapq.heappush(heap, (dist_sq, neighbor))

        # 处理堆中的位置
        while heap:
            dist_sq, p = heapq.heappop(heap)

            # 超出范围时停止
            if dist_sq > end_sq:
                break

            # 在范围内则加入结果
            if dist_sq >= start_sq:
                result.append(p)

            # 扩展新位置
            for dx, dy, dz in directions:
                neighbor = move_by_vector(p, dx, dy, dz)
                if neighbor is None:
                    continue
                n_coord = (neighbor.x, neighbor.y, Abstract3DRule.pos_index(board, neighbor))

                if n_coord in visited:
                    continue
                visited.add(n_coord)

                # 计算新位置到起点的距离平方
                new_dist_sq = (neighbor.x - x0) ** 2 + (neighbor.y - y0) ** 2 + (
                            Abstract3DRule.pos_index(board, neighbor) - z0) ** 2
                heapq.heappush(heap, (new_dist_sq, neighbor))

        return result


class Abstract3DMinesRule(AbstractMinesRule, ABC, Abstract3DRule):
    def __init__(self, board: AbstractBoard, data: str = None):
        Abstract3DRule.__init__(self, board, data)
        super().__init__(board, data)


class Abstract3DClueRule(AbstractClueRule, ABC, Abstract3DRule):
    def __init__(self, board: AbstractBoard, data: str = None):
        Abstract3DRule.__init__(self, board, data)
        super().__init__(board, data)


class Abstract3DMinesClueRule(AbstractMinesClueRule, ABC, Abstract3DRule):
    def __init__(self, board: AbstractBoard, data: str = None):
        Abstract3DRule.__init__(self, board, data)
        super().__init__(board, data)
