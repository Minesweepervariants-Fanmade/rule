from ortools.sat.python.cp_model_helper import IntVar

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.solver import Switch


class RuleSUD_(AbstractMinesRule):
    id = "SUD''"
    name = "Sudoku Box+"
    name.zh_CN = "数独宫+"
    doc = "Sudoku Box+: The board side length must be a multiple of 3. The board is evenly divided into 9 boxes, and numbers in each row, column, and box must be unique.(V only)"
    doc.zh_CN = "数独宫+：题板边长只能为3的整数倍，将题板均匀分为9个宫，每行每列每宫内数字不相同(仅限V, 雷上也有数字但无效)"
    tags = ["Original", 'Meta']
    author = ("NT", 24073104)
    creation_time = "2026-05-24 02:18:00"

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        bound = board.boundary()
        if bound.x != bound.y:
            raise ValueError("请输入一个正方形题板")
        if (bound.x + 1) % 3 != 0:
            raise ValueError("题板边长必须为3的整数倍")

    def create_constraints(self, board: 'Board', switch: 'Switch'):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            pos_bound = board.boundary(key=key)
            # 获取边界行和列的范围，计算边长
            rows = board.get_row_pos(pos_bound)
            cols = board.get_col_pos(pos_bound)
            n_rows = len(rows)
            n_cols = len(cols)

            # 检查边长是否为 3 的倍数且行列相等（标准正方形题板）
            if n_rows != n_cols or n_rows % 3 != 0:
                # 不符合题板要求，不添加约束（或可选择记录警告）
                continue

            block_size = n_rows // 3  # 每个宫的边长

            real_pos_sum = {
                pos: sum([
                    board.get_variable(_pos)
                    for _pos in pos.neighbors(2)
                    if board.is_valid(_pos)
                ]) for pos, _ in board(key=key)
            }
            # 限制取值种类数等于题板边长：变量取值范围为0..(n_rows-1)，共有n_rows种取值
            ub = max(0, n_rows - 1)
            pos_sum: dict[Position, IntVar] = {
                pos: model.new_int_var(0, ub, str(pos))
                for pos, _ in board(key=key)
            }

            # 确保 pos_sum 可取的种类数等于题板边长 n_rows
            # 方法：对于每个可能的值 v (0..ub)，为每个位置创建布尔变量 eq[pos,v]
            # 表示 pos_sum[pos]==v。保证每个位置恰有一个 v 为真，并且每个 v 至少被一个位置使用。
            eq = {}
            for pos in pos_sum:
                for v in range(ub + 1):
                    eq[(pos, v)] = model.new_bool_var(f"eq_{pos}_{v}")
                # 每个位置恰好有一个值
                model.add(sum(eq[(pos, v)] for v in range(ub + 1)) == 1)
                for v in range(ub + 1):
                    # 若 eq 为真，则强制 pos_sum[pos]==v
                    model.add(pos_sum[pos] == v).OnlyEnforceIf(eq[(pos, v)])

            # 每个值 v 必须至少出现在一个位置上，确保使用的不同值数量为 ub+1 (即 n_rows)
            for v in range(ub + 1):
                model.add(sum(eq[(pos, v)] for pos in pos_sum) >= 1)


            for pos, var in board(mode="var", key=key):
                model.add(real_pos_sum[pos] == pos_sum[pos]).OnlyEnforceIf(s, var.Not())


            col_positions = [
                [_pos for _pos in board.get_col_pos(pos)]
                for pos in rows
            ]

            row_positions = [
                [_pos for _pos in board.get_row_pos(pos)]
                for pos in cols
            ]

            for line in col_positions + row_positions:
                model.add_all_different(pos_sum[pos] for pos in line).OnlyEnforceIf(s)

            # 将位置按所在宫分组（使用坐标直接计算宫索引）
            boxes = {}
            for pos, _ in board(key=key):
                # 根据实际坐标计算宫索引（假设坐标从0开始连续）
                box_row = pos.x // block_size
                box_col = pos.y // block_size
                box_idx = (box_row, box_col)
                boxes.setdefault(box_idx, []).append(pos_sum[pos])

            # 每个宫内数字互不相同
            for var_list in boxes.values():
                if len(var_list) > 1:
                    model.add_all_different(var_list).OnlyEnforceIf(s)