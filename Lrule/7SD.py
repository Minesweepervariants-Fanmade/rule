from typing import List, Tuple, Dict, Set
from ortools.sat.python.cp_model import CpModel, IntVar

from ....abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.position import Position


class Rule7SD(AbstractMinesRule):
    id = "7SD"
    name = "Seven-Segment Display"
    name.zh_CN = "七段数码管"
    doc = "Each 3x5 area forms a 0-F digit; sum of mines in inner and outer cells equals the digit value"
    doc.zh_CN = "题板上至少有一个3x5区域形成0-F数字, 其相邻格的雷数之和等于该数字的值"
    author = ("NT", 2201963934)
    tags = ["Original", "Local", "Strong"]
    creation_time = "2026-07-15"

    # 段格在3x5区域中的相对坐标 (行, 列) — 5行×3列竖向布局
    SEGMENT_POSITIONS = [
        (0, 1),  # a段 (上横)
        (1, 2),  # b段 (右上竖)
        (3, 2),  # c段 (右下竖)
        (4, 1),  # d段 (下横)
        (3, 0),  # e段 (左下竖)
        (1, 0),  # f段 (左上竖)
        (2, 1),  # g段 (中横)
    ]

    # 顶点格在3x5区域中的相对坐标 — 5行×3列: 四角 + 左右两边中点
    VERTEX_POSITIONS = [
        (0, 0),  # 左上角
        (0, 2),  # 右上角
        (2, 0),  # 左边中点
        (2, 2),  # 右边中点
        (4, 0),  # 左下角
        (4, 2),  # 右下角
    ]

    # 内面格在3x5区域中的相对坐标 — 5行×3列: 中心格上下两格
    INNER_POSITIONS = [
        (1, 1),  # 中心上格
        (3, 1),  # 中心下格
    ]

    # 标准七段数码管段状态 (a,b,c,d,e,f,g) 对应上述SEGMENT_POSITIONS顺序
    # 0-F数字的七段编码 (1=亮, 0=灭)
    SEVEN_SEGMENT_CODES = {
        0: (1, 1, 1, 1, 1, 1, 0),  # 0
        1: (0, 1, 1, 0, 0, 0, 0),  # 1
        2: (1, 1, 0, 1, 1, 0, 1),  # 2
        3: (1, 1, 1, 1, 0, 0, 1),  # 3
        4: (0, 1, 1, 0, 0, 1, 1),  # 4
        5: (1, 0, 1, 1, 0, 1, 1),  # 5
        6: (1, 0, 1, 1, 1, 1, 1),  # 6
        7: (1, 1, 1, 0, 0, 0, 0),  # 7
        8: (1, 1, 1, 1, 1, 1, 1),  # 8
        9: (1, 1, 1, 1, 0, 1, 1),  # 9
        10: (1, 1, 1, 0, 1, 1, 1),  # A
        11: (0, 0, 1, 1, 1, 1, 1),  # b
        12: (1, 0, 0, 1, 1, 1, 0),  # C
        13: (0, 1, 1, 1, 1, 0, 1),  # d
        14: (1, 0, 0, 1, 1, 1, 1),  # E
        15: (1, 0, 0, 0, 1, 1, 1),  # F
    }

    # 预计算每个数字的7段图案
    PATTERNS: Dict[int, Tuple[int, ...]] = {}

    # 顶点到连接段的映射 (顶点索引 -> 连接的段索引列表)
    VERTEX_SEGMENT_MAP = [
        [0, 5],           # V0(0,0): a, f
        [0, 1],           # V1(0,2): a, b
        [5, 6, 4],        # V2(2,0): f, g, e
        [1, 6, 2],        # V3(2,2): b, g, c
        [4, 3],           # V4(4,0): e, d
        [2, 3],           # V5(4,2): c, d
    ]

    @classmethod
    def _build_patterns(cls):
        """构建每个数字的7段图案"""
        if cls.PATTERNS:
            return
        for digit, seg_code in cls.SEVEN_SEGMENT_CODES.items():
            cls.PATTERNS[digit] = seg_code  # 7个元素

    def __init__(self, board: "Board | None" = None, data: str | None = None):
        super().__init__(board, data)
        self.min_segments = 1      # 默认至少1个数码管
        self.mine_placement = False  # 默认不加雷排布约束
        if data is not None:
            import re
            m = re.match(r'^(\d+)(!?)$', data)
            if m:
                self.min_segments = int(m.group(1))
                self.mine_placement = (m.group(2) == '!')

    def create_constraints(self, board: 'Board', switch):
        """
        为CP-SAT模型添加约束
        """
        self._build_patterns()

        model: CpModel = board.get_model()

        # 获取主交互式题板的尺寸
        main_key = board.get_interactive_keys()[0]
        boundary_pos = board.boundary(main_key)
        # Position(col, row)构造函数, boundary返回Position(cols-1, rows-1)
        rows = boundary_pos.row + 1
        cols = boundary_pos.col + 1
        # 遍历所有可能的3x5区域 (5行×3列竖向)
        regions = []
        for r in range(rows - 4):
            for c in range(cols - 2):
                # 检查区域内所有15个位置是否有效 (在棋盘内且未被掩码遮挡)
                all_positions = []
                valid = True
                for i in range(5):
                    for j in range(3):
                        pos = Position(c + j, r + i, main_key)
                        if not board.is_valid(pos):
                            valid = False
                            break
                        all_positions.append(pos)
                    if not valid:
                        break
                if not valid:
                    continue

                # 获取内部15个位置的变量
                pos_vars = [board.get_variable(pos) for pos in all_positions]

                # 获取段格变量 (7个) — 索引 = dr * 3 + dc (每行3列)
                seg_vars = []
                for dr, dc in self.SEGMENT_POSITIONS:
                    idx = dr * 3 + dc
                    seg_vars.append(pos_vars[idx])

                # 获取顶点格变量 (6个)
                vertex_vars = []
                for dr, dc in self.VERTEX_POSITIONS:
                    idx = dr * 3 + dc
                    vertex_vars.append(pos_vars[idx])

                # 获取内面格变量 (2个)
                inner_vars = []
                for dr, dc in self.INNER_POSITIONS:
                    idx = dr * 3 + dc
                    inner_vars.append(pos_vars[idx])

                # 获取外面格变量: 上下各3格, 左右各5格
                # 外面格在盘面外视为非雷格(值为0), 无需添加变量
                # 注意: 必须用 Position(col, row) 而不是 board.get_pos, 因为 get_pos 对负坐标做环绕
                outer_vars = []
                # 上方3格 (行r-1, 列c到c+2)
                for j in range(3):
                    pos = Position(c + j, r - 1, main_key)
                    if board.is_valid(pos):
                        outer_vars.append(board.get_variable(pos))
                # 下方3格 (行r+5, 列c到c+2)
                for j in range(3):
                    pos = Position(c + j, r + 5, main_key)
                    if board.is_valid(pos):
                        outer_vars.append(board.get_variable(pos))
                # 左方5格 (列c-1, 行r到r+4)
                for i in range(5):
                    pos = Position(c - 1, r + i, main_key)
                    if board.is_valid(pos):
                        outer_vars.append(board.get_variable(pos))
                # 右方5格 (列c+3, 行r到r+4)
                for i in range(5):
                    pos = Position(c + 3, r + i, main_key)
                    if board.is_valid(pos):
                        outer_vars.append(board.get_variable(pos))

                regions.append((seg_vars, vertex_vars, inner_vars, outer_vars, r, c))

        # 用于收集所有区域的is_segment变量，确保至少有一个数码管
        segment_vars = []

        # 为每个区域创建约束
        for seg_vars, vertex_vars, inner_vars, outer_vars, r, c in regions:
            # 7段格的状态变量 (匹配0-F数码管标准图案)
            pattern_vars = seg_vars

            # 创建数字变量 digit (0-15)，仅在是数码管时有效
            digit = model.NewIntVar(0, 15, f'digit_{r}_{c}')

            # 为每个数字d创建匹配标志 is_digit_d
            is_d_vars = []
            for d, pattern in self.PATTERNS.items():
                is_d = model.NewBoolVar(f'is_digit_{r}_{c}_{d}')

                # 构建匹配条件: 所有要求为1的位置变量为1，所有要求为0的位置变量为0
                conditions = []
                for var, state in zip(pattern_vars, pattern):
                    if state == 1:
                        conditions.append(var)
                    else:
                        # 要求为0，即 (1 - var) 为真
                        conditions.append(var.Not())

                # is_d => AND(conditions): 每个条件 -> AddBoolOr([Not(is_d), cond])
                for cond in conditions:
                    model.AddBoolOr([is_d.Not(), cond])

                # AND(conditions) => is_d: 如果所有条件满足, 则必须是数字d
                not_conds = [cond.Not() for cond in conditions]
                model.AddBoolOr(not_conds + [is_d])

                is_d_vars.append(is_d)

            # 确保最多只有一个数字被匹配 (即图案不能同时匹配多个数字)
            model.AddAtMostOne(is_d_vars)

            # 该区域是否是数码管 (即至少匹配一个数字)
            is_segment = model.NewBoolVar(f'is_segment_{r}_{c}')
            model.Add(sum(is_d_vars) == is_segment)

            # digit 等于匹配的数字
            model.Add(digit == sum(d * is_d for d, is_d in enumerate(is_d_vars)))

            # 数码管的内面格必须为非雷 (非数码管时无约束)
            for v in inner_vars:
                model.Add(v <= 1 - is_segment)

            # 外面格的雷数之和 == digit (Big-M)
            sum_outer = sum(outer_vars)
            M = len(outer_vars) + 15
            model.Add(sum_outer <= digit + M * (1 - is_segment))
            model.Add(sum_outer >= digit - M * (1 - is_segment))

            # 数码管的顶点格由连接的段决定 (非数码管时约束不激活)
            for v_idx, seg_indices in enumerate(self.VERTEX_SEGMENT_MAP):
                v = vertex_vars[v_idx]
                connected_segs = [seg_vars[si] for si in seg_indices]
                # 正向: 任何连接的段是雷 → 顶点必须是雷
                for s in connected_segs:
                    model.AddBoolOr([s.Not(), v, is_segment.Not()])
                # 反向: 顶点是雷 → 至少一个连接的段是雷
                model.AddBoolOr([is_segment.Not(), v.Not()] + connected_segs)

            # 收集该区域的 is_segment 变量，用于确保至少有一个数码管
            segment_vars.append(is_segment)

        # 确保至少 self.min_segments 个数码管 (无区域时 sum=0, 自动不可满足)
        model.Add(sum(segment_vars) >= self.min_segments)

        # 雷排布约束: 雷只能在段格/顶点格/外面格中
        if self.mine_placement:
            allowed: set[Position] = set()
            for seg_vars, vertex_vars, inner_vars, outer_vars, r, c in regions:
                for dr, dc in self.SEGMENT_POSITIONS:
                    allowed.add(Position(c + dc, r + dr, main_key))
                for dr, dc in self.VERTEX_POSITIONS:
                    allowed.add(Position(c + dc, r + dr, main_key))
                # 外面格
                for j in range(3):
                    p = Position(c + j, r - 1, main_key)
                    if board.is_valid(p):
                        allowed.add(p)
                for j in range(3):
                    p = Position(c + j, r + 5, main_key)
                    if board.is_valid(p):
                        allowed.add(p)
                for i in range(5):
                    p = Position(c - 1, r + i, main_key)
                    if board.is_valid(p):
                        allowed.add(p)
                for i in range(5):
                    p = Position(c + 3, r + i, main_key)
                    if board.is_valid(p):
                        allowed.add(p)
            # 禁止在允许集之外的格放雷
            row_max = board.boundary(main_key).row + 1
            col_max = board.boundary(main_key).col + 1
            for row in range(row_max):
                for col in range(col_max):
                    p = Position(col, row, main_key)
                    if p not in allowed and board.is_valid(p):
                        model.Add(board.get_variable(p) == 0)

    def suggest_total(self, info: dict):
        """
        建议雷总数
        对于七段数码管规则，雷数应该适中，使得至少有一个区域能形成数码管图案。
        """
        ub = 0
        totals = info.get("total", {})
        interactive = info.get("interactive", [])
        soft_fn = info.get("soft_fn")

        if not isinstance(totals, dict) or not isinstance(interactive, list) or not callable(soft_fn):
            return

        for key in interactive:
            ub += totals.get(key, 0)

        # 建议雷数约为总格数的40%，这样既不太密也不太疏，容易形成图案
        soft_fn(ub * 0.4, -1)
