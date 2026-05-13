"""
[3M@] 落差: 雷线索表示它到该列最高的雷的高度差与它到该列最低的雷的高度差的差的绝对值
作者: 小小神中医 (3086842243)
最后编辑时间: 2026-03-01 13:28:35
"""

from ortools.sat.python.cp_model import IntVar
from ....abs.Mrule import AbstractMinesClueRule, AbstractMinesValue
from ....abs.board import AbstractBoard, AbstractPosition


class Rule3MAt(AbstractMinesClueRule):
    id = "3M@"
    name = "HeightDifference"
    name.zh_CN = "落差"
    doc = "Mine clue indicates the absolute difference between its vertical distance to the highest mine and to the lowest mine in its column"
    doc.zh_CN = "雷线索表示它到该列最高的雷的高度差与它到该列最低的雷的高度差的差的绝对值"
    author = ("小小神中医", 3086842243)
    tags = ["Creative", "Local", "Mine-Position"]
    creation_time = "2026-03-01"

    def fill(self, board: AbstractBoard) -> AbstractBoard:
        for key in board.get_interactive_keys():
            # 预计算每列的雷位置范围
            col_mins = {}
            col_maxs = {}
            for pos, _ in board("F", key=key):
                col = pos.y
                x = pos.x
                if col not in col_mins:
                    col_mins[col] = x
                    col_maxs[col] = x
                else:
                    col_mins[col] = min(col_mins[col], x)
                    col_maxs[col] = max(col_maxs[col], x)
            # 设置每个雷格的线索值
            for pos, _ in board("F", key=key):
                col = pos.y
                if col in col_mins:
                    min_x = col_mins[col]
                    max_x = col_maxs[col]
                    value = abs(max_x + min_x - 2 * pos.x)
                    board.set_value(pos, Value3MAt(pos, value))
        return board

    def create_constraints(self, board: AbstractBoard, switch):
        model = board.get_model()
        rule_switch = switch.get(model, self)
        for key in board.get_interactive_keys():
            boundary = board.boundary(key)
            col_positions = board.get_col_pos(boundary)
            # 创建每列的 min, max 变量以及是否有雷的标志
            col_min_var = {}
            col_max_var = {}
            col_has_mine = {}
            for col_pos in col_positions:
                y = col_pos.y
                col_min_var[y] = model.NewIntVar(0, boundary.x, f"3M@_min_{key}_{y}")
                col_max_var[y] = model.NewIntVar(0, boundary.x, f"3M@_max_{key}_{y}")
                col_has_mine[y] = model.NewBoolVar(f"3M@_has_mine_{key}_{y}")

            # 存储每列的最小/最大候选变量
            col_min_candidates = {y: [] for y in col_min_var}
            col_max_candidates = {y: [] for y in col_min_var}

            # 收集该列所有雷格变量和位置
            col_mine_vars = {y: [] for y in col_min_var}
            col_mine_positions = {y: [] for y in col_min_var}

            for pos, mine_var in board(mode="variable", key=key, special='raw'):
                y = pos.y
                if y not in col_min_var:
                    continue
                col_mine_vars[y].append(mine_var)
                col_mine_positions[y].append(pos.x)
                min_var = col_min_var[y]
                max_var = col_max_var[y]
                has_mine = col_has_mine[y]

                # 该列至少有一个雷
                model.Add(has_mine == 1).OnlyEnforceIf(mine_var)

                # 雷的 x 必须位于 [min, max] 区间内
                model.Add(min_var <= pos.x).OnlyEnforceIf(mine_var)
                model.Add(max_var >= pos.x).OnlyEnforceIf(mine_var)

                # 候选变量：该格可能是该列的最小雷或最大雷
                is_min = model.NewBoolVar(f"3M@_is_min_{key}_{pos.x}_{pos.y}")
                is_max = model.NewBoolVar(f"3M@_is_max_{key}_{pos.x}_{pos.y}")
                model.Add(is_min <= mine_var)
                model.Add(is_max <= mine_var)
                model.Add(pos.x == min_var).OnlyEnforceIf(is_min)
                model.Add(pos.x == max_var).OnlyEnforceIf(is_max)
                col_min_candidates[y].append(is_min)
                col_max_candidates[y].append(is_max)

            # 对每列，如果有雷，则至少有一个最小候选和一个最大候选为真
            for y in col_min_candidates:
                has_mine = col_has_mine[y]
                model.Add(sum(col_min_candidates[y]) >= 1).OnlyEnforceIf(has_mine)
                model.Add(sum(col_max_candidates[y]) >= 1).OnlyEnforceIf(has_mine)

            # 不强制每列必须有雷；允许空列（空列不会产生线索，不参与约束）

            # 额外约束：对于每列，如果存在雷，则 min 和 max 必须分别为该列最小和最大的雷位置
            # 通过强制所有雷格的位置必须在 [min, max] 之间，且存在雷等于 min 和 max，已经足够。
            # 但还需要约束：没有任何雷的位置小于 min 或大于 max，已经由不等式保证。

            # 为每个线索格（雷格）添加值约束
            for pos, obj in board("F", key=key):
                if not isinstance(obj, Value3MAt):
                    continue
                y = pos.y
                if y not in col_min_var:
                    continue
                min_var = col_min_var[y]
                max_var = col_max_var[y]
                sum_expr = max_var + min_var - 2 * pos.x
                abs_diff = model.NewIntVar(0, boundary.x * 2, f"3M@_abs_{key}_{pos.x}_{pos.y}")
                model.AddAbsEquality(abs_diff, sum_expr)
                model.Add(abs_diff == obj.value).OnlyEnforceIf(rule_switch)


class Value3MAt(AbstractMinesValue):
    def __init__(self, pos: AbstractPosition, value: int = 0, code: bytes = None):
        super().__init__(pos, code)
        if code is not None:
            self.value = int.from_bytes(code, 'big')
        else:
            self.value = value

    def __repr__(self):
        return str(self.value)

    @classmethod
    def type(cls) -> bytes:
        return Rule3MAt.id.encode('ascii')

    def code(self) -> bytes:
        return self.value.to_bytes(2, 'big')

    def weaker(self, board: AbstractBoard):
        return self

    def weaker_times(self) -> int:
        return 0

    def create_constraints(self, board: AbstractBoard, switch):
        # 约束已在规则类中统一实现，此处留空
        pass
