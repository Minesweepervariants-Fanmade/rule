#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2025/06/09 11:37
# @Author  : xxx
# @FileName: 3Ap.py
from itertools import product
from typing import List, Dict, Set, Tuple

from ortools.sat.python.cp_model import IntVar

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from ....abs.board import AbstractBoard, AbstractPosition
from ....utils.impl_obj import MINES_TAG, VALUE_QUESS


def put(board, pos: 'AbstractPosition', path):
    value = 0
    while board.in_bounds(pos):
        value += 1
        if board.get_type(pos) == "F":
            path += 1
            path %= 4
        else:
            obj = board.get_value(pos)
            obj: Value3Ap
            obj.append(value)
            path += 3
            path %= 4
        # 0.上 1.右 2.下 3.左
        match path:
            case 0:
                pos = pos.down()
            case 1:
                pos = pos.left()
            case 2:
                pos = pos.up()
            case 3:
                pos = pos.right()


class Rule3Ap(AbstractClueRule):
    id = "3A^"
    name = "Langton's Ant - XOR"
    name.zh_CN = "兰顿蚂蚁·异或"
    doc = "将兰顿蚂蚁[3A]四个方向的结果做异或操作 若结果为无穷大则使用补码形式显示"
    author = ("雾", 3140864122)

    def fill(self, board: 'AbstractBoard') -> 'AbstractBoard':
        for pos, _ in board("N"):
            board.set_value(pos, Value3Ap(pos))
        lines = [
            board.get_row_pos(board.get_pos(0, 0)),
            board.get_col_pos(board.get_pos(-1, -1)),
            board.get_row_pos(board.get_pos(-1, -1)),
            board.get_col_pos(board.get_pos(0, 0)),
        ]
        for index in range(4):
            line = lines[index]
            for pos in line:
                put(board, pos, index)
                # print(pos, index)
                # print(board.show_board())
        for _, obj in board("C"):
            obj: Value3Ap
            obj.end()
        return board


class Value3Ap(AbstractClueValue):
    def __init__(self, pos: 'AbstractPosition', code: bytes = b''):
        super().__init__(pos)
        if not code:
            self.value = 0
            self.data = []
            return
        self.value = code[0] - 128  # 路径异或值

    def __str__(self) -> str:
        return f"{self.value}"

    def __repr__(self) -> str:
        return f"{self.value}"

    def high_light(self, board: 'AbstractBoard') -> List['AbstractPosition']:
        pos = self.pos.clone()
        position = []
        for path_dir in range(4):
            path = path_dir
            while True:
                if not board.in_bounds(pos):
                    break
                if board.get_type(pos) == "N":
                    position.append(pos)
                    break
                if pos in position:
                    break
                position.append(pos)
                # 0.上 1.右 2.下 3.左
                if board.get_type(pos) == "F":
                    path += 3
                    path %= 4
                else:
                    path += 1
                    path %= 4
                match path:
                    case 0:
                        pos = pos.down()
                    case 1:
                        pos = pos.left()
                    case 2:
                        pos = pos.up()
                    case 3:
                        pos = pos.right()
                if (
                    pos == self.pos and
                    path == (path_dir + 1) % 4
                ):
                    break
        return position

    def append(self, data):
        self.data.append(data)

    def end(self):
        self.data: list[int]
        self.data += [-1] * (4 - len(self.data))

        # 提取所有首个int值
        self.value = (self.data[0] ^ self.data[1]) ^ (self.data[2] ^ self.data[3])
        # get_logger().debug(f"[3A^] {self.pos} {self.data},value {self.value}")

    @classmethod
    def type(cls) -> bytes:
        return Rule3Ap.id.encode("ascii")

    def code(self) -> bytes:
        return bytes([self.value + 128])

    # def bfs_get_states(self, board: 'AbstractBoard') -> List[dict]:
    #     """
    #     大致思路:
    #     从方向开始走 如果提前走出边境或者循环就直接丢弃 如果刚好在值内就记录
    #
    #     一层具象
    #     从当前位置为根节点构建一棵二叉树进行遍历
    #     如果说value==-1 那么需要进入while遍历并把所有走出题板的节点删除
    #     如果value>=1 那么就使用range()
    #
    #     二层具象
    #     如果值为无穷 那么需要使用快慢节点进行遍历 一旦重合就立刻将其值放入list
    #     可能会遇到重复的pos节点 在遍历的时候需要边查表边遍历
    #     如果出现过就需要直接赋值而不是继续分叉
    #
    #     三层具象
    #     针对>=1可以使用ab_bfs列表 对当前abfs进行遍历
    #     如果出现超出题板 那么就丢出
    #     如果出现循环 不用管 等时间到了他就死了
    #     每次创建叉的时候需要查看当前经过的路径是否遍历过
    #
    #     >=1:
    #         需要附带的信息有 当前节点, 当前方向, 遍历过的路径的对应值
    #         具体步骤为:
    #             沿着当前方向走一步
    #             查看当前节点有没有超出题板内
    #                 超出题板就撇了
    #             查看当前节点在不在对应值列表里面
    #                 不在就加入对应值列表
    #             加入b_bfs
    #     """
    #
    #     def move(_pos, _dir):
    #         match _dir:
    #             case 0:
    #                 _pos = _pos.up()
    #             case 1:
    #                 _pos = _pos.right()
    #             case 2:
    #                 _pos = _pos.down()
    #             case 3:
    #                 _pos = _pos.left()
    #         return _pos
    #
    #     def node(_pos, _dt, _value_map):
    #         result = []
    #         if _pos in _value_map:
    #             # 如果在就继续走
    #             result.append((_pos, (_dt + _value_map[_pos] * 2 + 1) % 4, _value_map.copy()))
    #         else:
    #             if (pos_type := board.get_type(_pos)) != "N":
    #                 # 当前位置是有值的 直接拿了用
    #                 _value_map = _value_map.copy()
    #                 _value_map[_pos] = 0 if pos_type == "C" else 1
    #                 result.append((_pos, (_dt + _value_map[_pos] * 2 + 1) % 4, _value_map))
    #             else:
    #                 # 如果不在说明未经过过该节点 就加入map
    #                 _value_map_a = _value_map.copy()
    #                 _value_map_b = _value_map.copy()
    #                 _value_map_a[_pos] = 1
    #                 _value_map_b[_pos] = 0
    #                 result.extend([
    #                     (_pos, (_dt + 3) % 4, _value_map_a),
    #                     (_pos, (_dt + 1) % 4, _value_map_b),
    #                 ])
    #         return result
    #
    #     root = self.pos.clone()
    #     a_bfs = [(root, self.dir, {root.clone(): 0})]
    #     b_bfs = []
    #     answer_list = []
    #
    #     if self.value == 0:
    #         flag = False
    #         # 处理循环的情况
    #         while len(a_bfs) > 0:
    #             for pos, dt, value_map in a_bfs:
    #                 if flag and pos == self.pos and dt == self.dir:
    #                     # 如果当前位置和方向和自身完全相同 就说明循环了
    #                     answer_list.append(value_map)
    #                     continue
    #                 # 沿着当前方向走一步
    #                 # 0.上 1.右 2.下 3.左
    #                 pos = move(pos, dt)
    #                 if not board.in_bounds(pos):
    #                     # 查看当前节点有没有超出题板内
    #                     continue
    #                 b_bfs.extend(node(pos, dt, value_map))
    #             a_bfs = b_bfs
    #             b_bfs = []
    #             flag = True
    #         return answer_list
    #     else:
    #         for depth in range(self.value, 0, -1):
    #             for pos, dt, value_map in a_bfs:
    #                 # 沿着当前方向走一步
    #                 # 0.上 1.右 2.下 3.左
    #                 pos = move(pos, dt)
    #                 # 查看当前节点有没有超出题板内
    #                 if not board.in_bounds(pos):
    #                     # 如果depth==self.value就是要的这个结果
    #                     if depth == 1:
    #                         answer_list.append(value_map)
    #                     continue
    #                 b_bfs.extend(node(pos, dt, value_map))
    #             a_bfs = b_bfs
    #             b_bfs = []
    #         return answer_list
    #
    # def deduce_cells(self, board: 'AbstractBoard') -> bool:
    #     # 开玩笑 还真能写
    #     answer_list = self.bfs_get_states(board)
    #     pos_map = {}
    #     for line in answer_list:
    #         for pos in line:
    #             if pos not in pos_map:
    #                 pos_map[pos] = [line[pos], 1]
    #             else:
    #                 if pos_map[pos][0] == line[pos]:
    #                     pos_map[pos][1] += 1
    #     change = False
    #     for pos in pos_map:
    #         if pos_map[pos][1] == len(answer_list):
    #             if board.get_type(pos) == "N":
    #                 if pos_map[pos][0]:
    #                     board.set_value(pos, MINES_TAG)
    #                 else:
    #                     board.set_value(pos, VALUE_QUESS)
    #                 change = True
    #     return change

    def _enumerate_direction(
        self, board: 'AbstractBoard',
        pos_main: 'AbstractPosition', init_dir: int,
        direction: int, steps: int,
        constraints: Dict['AbstractPosition', int],
        visited: Set[Tuple['AbstractPosition', int]],
        result: Dict[int, List[IntVar]],
        all_switch: IntVar
    ):
        visited.add((pos_main, direction))
        pos = self._move(pos_main, direction)

        if pos in [i[0] for i in visited]:  # 循环
            if board.get_type(pos) == "C":
                new_dir = (direction + 1) % 4
            elif board.get_type(pos) == "F":
                new_dir = (direction + 3) % 4
            else:
                new_dir = (direction + 1 + 2 * constraints[pos]) % 4
            if (pos, new_dir) in visited:
                model = board.get_model()
                cond = model.NewBoolVar(f"[3A^]{self.pos}_{init_dir}_-1")
                if -1 not in result:
                    result[-1] = []
                result[-1].append(cond)
                _board = board.clone()
                for pos, val in constraints.items():
                    model.Add(board.get_variable(pos) == val).OnlyEnforceIf(cond, all_switch)
                    _board.set_value(pos, MINES_TAG if val else VALUE_QUESS)
                return

        if not board.in_bounds(pos):    # 出界
            _board = board.clone()
            model = board.get_model()
            cond = model.NewBoolVar(f"[3A^]{self.pos}_{init_dir}_{steps}")
            if steps not in result:
                result[steps] = []
            result[steps].append(cond)
            for pos, val in constraints.items():
                model.Add(board.get_variable(pos) == val).OnlyEnforceIf(cond, all_switch)
                _board.set_value(pos, MINES_TAG if val else VALUE_QUESS)
            return

        cell_type = board.get_type(pos, special='raw')
        if cell_type == "F" or constraints.get(pos, -1) == 1:
            # 雷：左转
            new_dir = (direction + 3) % 4
            self._enumerate_direction(
                board, pos, init_dir,
                new_dir, steps + 1,
                constraints, visited, result,
                all_switch
            )
        elif cell_type == "C" or constraints.get(pos, -1) == 0:
            # 线索格（视为非雷）：右转
            new_dir = (direction + 1) % 4
            self._enumerate_direction(
                board, pos, init_dir,
                new_dir, steps + 1,
                constraints, visited, result,
                all_switch
            )
        else:  # "N"
            # 分支1：假设为雷
            cons_mine = constraints.copy()
            cons_mine[pos] = 1
            new_dir_mine = (direction + 3) % 4
            new_visited = visited.copy()
            self._enumerate_direction(
                board, pos, init_dir,
                new_dir_mine, steps + 1,
                cons_mine, new_visited, result,
                all_switch
            )

            # 分支2：假设为非雷
            cons_non = constraints.copy()
            cons_non[pos] = 0
            new_dir_non = (direction + 1) % 4
            new_visited = visited.copy()
            self._enumerate_direction(
                board, pos, init_dir,
                new_dir_non, steps + 1,
                cons_non, new_visited, result,
                all_switch
            )

    def _move(self, pos, direction) -> 'AbstractPosition':
        if direction == 0:
            return pos.up()
        elif direction == 1:
            return pos.right()
        elif direction == 2:
            return pos.down()
        else:  # direction == 3
            return pos.left()

    def create_constraints(self, board: 'AbstractBoard', switch):
        model = board.get_model()
        s = switch.get(model, self)
        result: dict[int, dict[int, list[IntVar]]] = dict()
        for dir_path in range(4):
            result[dir_path] = {}
            self._enumerate_direction(
                board, self.pos, dir_path,
                dir_path, 1,
                dict(), set(), result[dir_path],
                s
            )
            # model.AddBoolOr([cond for conds in result[dir_path].values() for cond in conds]).OnlyEnforceIf(s)

        # 枚举所有步数组合，直接生成总变量
        steps_lists = [list(result[d].keys()) for d in range(4)]
        combo_vars = []
        for combo in product(*steps_lists):
            a, b, c, d = combo
            if ((a ^ b) ^ (c ^ d)) != self.value:
                continue
            combo_var = model.NewBoolVar(f"combo_{self.pos}_{a}_{b}_{c}_{d}")
            for idx, step in enumerate(combo):
                model.AddBoolOr(result[idx][step]).OnlyEnforceIf([combo_var, s])
            combo_vars.append(combo_var)
        model.AddBoolOr(combo_vars).OnlyEnforceIf(s)
