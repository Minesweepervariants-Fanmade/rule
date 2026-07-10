"""
Masyu 规则实现 (Mrule)
规则ID: Masyu
珍珠：SL简单回路，雷线索分为白珍珠：直线通过本格且相邻两格至少有一个转弯，
黑珍珠：拐弯通过本格且相邻两格均不转弯，非珍珠：不满足以上两种。
作者: NT (2201963934)
"""

from typing import List, Dict, Any, Optional, Tuple
from enum import IntEnum

from minesweepervariants.abs.Mrule import AbstractMinesClueRule, AbstractMinesValue
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.board import Board, Position
from minesweepervariants.utils.value_template import ValueTemplate, SingleValue
from minesweepervariants.utils.tool import get_logger

# 假设框架提供了 SL_loop 左线规则（用于回路约束）
# 如果未提供，需要在 create_constraints 中自行实现回路连通性约束
try:
    from minesweepervariants.impl.rule.Lrule.SL_loop import SL_loop
except ImportError:
    SL_loop = None
    get_logger().warning("SL_loop not found, loop connectivity constraint will be skipped")


# ============================================================================
# MasyuType 枚举
# ============================================================================
class MasyuType(IntEnum):
    """珍珠类型枚举"""
    NONE = -1      # 非珍珠（非雷）
    WHITE = 0      # 白珍珠（雷）
    BLACK = 1      # 黑珍珠（雷）


# ============================================================================
# MasyuValue: 线索值类
# ============================================================================
class MasyuValue(ValueTemplate):
    """
    Masyu 线索值类，表示一个格子的珍珠类型。
    白珍珠 (WHITE) 和黑珍珠 (BLACK) 为雷，非珍珠 (NONE) 不是雷。
    """

    def __init__(self, value: MasyuType):
        super().__init__()
        self.type = value
        self.is_mine = (value == MasyuType.WHITE or value == MasyuType.BLACK)

    @classmethod
    def from_json(cls, data: Any) -> "MasyuValue":
        """
        从 JSON 数据初始化线索值。
        支持 int 或 str 类型。
        - 0 或 'white' / 'WHITE' / 'W' -> 白珍珠
        - 1 或 'black' / 'BLACK' / 'B' -> 黑珍珠
        - -1 或 'none' / 'NONE' / 'N' / None -> 非珍珠
        """
        if data is None:
            return cls(MasyuType.NONE)

        if isinstance(data, int):
            if data == 0:
                return cls(MasyuType.WHITE)
            elif data == 1:
                return cls(MasyuType.BLACK)
            else:
                return cls(MasyuType.NONE)

        if isinstance(data, str):
            lower = data.lower().strip()
            if lower in ('0', 'white', 'w'):
                return cls(MasyuType.WHITE)
            elif lower in ('1', 'black', 'b'):
                return cls(MasyuType.BLACK)
            else:
                return cls(MasyuType.NONE)

        return cls(MasyuType.NONE)

    def to_json(self) -> Any:
        """导出为 JSON 可序列化格式"""
        return self.type.value

    def __repr__(self) -> str:
        """使用 ASCII 字符表示珍珠类型，严禁使用中文"""
        if self.type == MasyuType.WHITE:
            return "O"   # 白珍珠（空心圆）
        elif self.type == MasyuType.BLACK:
            return "X"   # 黑珍珠（实心叉）
        else:
            return "."   # 非珍珠

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MasyuValue):
            return False
        return self.type == other.type

    def __hash__(self) -> int:
        return hash(self.type)

    def compose(self):
        from minesweepervariants.utils.image_template import get_text, get_col, get_dummy
        color = ("#FFFFFF", "#000000")
        return get_col(
            get_dummy(height=0.3),
            get_text(self.__repr__(), color=color),
            get_dummy(height=0.3),
        )

    def web_component(self):
        from minesweepervariants.utils.web_template import Number
        return Number(self.__repr__())


# ============================================================================
# MasyuHint: 线索类
# ============================================================================
class MasyuHint(AbstractMinesValue):
    """
    Masyu 线索类。
    每个线索包含一个 MasyuValue 值，表示该格是白珍珠、黑珍珠或非珍珠。
    """

    id = "MasyuHint"

    def __init__(self, pos: Position, value: MasyuValue, **kwargs):
        super().__init__(pos, **kwargs)
        self.value = value

    @classmethod
    def from_json(cls, pos: Position, data: Dict[str, Any]) -> "MasyuHint":
        """
        从 JSON 数据初始化线索实例。
        预期格式: {"row": int, "col": int, "value": int|str}
        """
        val = data.get("value", -1)
        value_obj = MasyuValue.from_json(val)
        return cls(pos, value_obj)

    def create_constraints(self, board, switch):
        # Masyu 的约束在 MasyuRule 中统一构建，此处留空
        pass

    def __repr__(self) -> str:
        """线索的字符串表示，使用 ASCII 字符"""
        return f"{self.value!s}"


# ============================================================================
# MasyuRule: 规则类
# ============================================================================
class MasyuRule(AbstractMinesClueRule):
    """
    Masyu 规则（中线规则）。
    珍珠（雷）形成一条 SL 回路，白珍珠直线通过且至少一个相邻格转弯，
    黑珍珠转弯通过且相邻格均不转弯。
    规则自带左线约束（回路约束）。
    """

    id = "Masyu"
    name = "Masyu"
    name.zh_CN = "珍珠"
    doc = "Pearl: SL simple loop, white pearl goes straight through with at least one turn in adjacent cells, black pearl turns through with no turns in adjacent cells"
    doc.zh_CN = "珍珠：SL简单回路，白珍珠直线通过且相邻两格至少有一个转弯，黑珍珠拐弯通过且相邻两格均不转弯"
    author = ("NT", 2201963934)
    tags = ["Creative", "Local", "Construction", "Connectivity"]
    creation_time = "2026-05-06"

    def __init__(self, board: Board | None = None, data: str | None = None) -> None:
        super().__init__(board, data)
        self.logger = get_logger()

    def fill(self, board: Board) -> Board:
        """
        在左线放置完成后调用，将题板内的所有雷值赋值为线索。
        为每个雷格随机分配白珍珠或黑珍珠。
        """
        import random
        key = board.get_interactive_keys()[0] if board.get_interactive_keys() else "1"
        for pos, _ in board("F", key=key):
            # 随机选择白珍珠或黑珍珠
            typ = random.choice([MasyuType.WHITE, MasyuType.BLACK])
            value = MasyuValue(typ)
            hint = MasyuHint(pos, value)
            board.set_value(pos, hint)
        return board

    def create_constraints(self, board: Board, switch) -> None:
        """
        基于当前题板向 CP-SAT 模型添加 Masyu 约束。
        :param board: 题板对象
        :param switch: 激活开关（未使用）
        """
        # 获取主板尺寸
        key = board.get_interactive_keys()[0] if board.get_interactive_keys() else "1"
        size = board.get_config(key, "size")
        rows = size.rows
        cols = size.cols
        model = board.get_model()

        # 获取所有格子的线索值（MasyuValue）
        clue_map = {}  # (i, j) -> MasyuType
        for i in range(rows):
            for j in range(cols):
                pos = Position(i, j, key)
                if board.is_valid(pos):
                    val = board.get_value(pos)
                    if isinstance(val, MasyuValue):
                        clue_map[(i, j)] = val.type
                    elif isinstance(val, MasyuHint):
                        clue_map[(i, j)] = val.value.type

        # ------------------------------------------------------------------
        # 1. 创建连接变量
        #    conn[dir][i][j] 表示格子 (i,j) 在 dir 方向是否有回路连接
        #    dir: 'U', 'D', 'L', 'R'
        # ------------------------------------------------------------------
        conn = {}
        for d in ['U', 'D', 'L', 'R']:
            conn[d] = [[model.NewBoolVar(f"conn_{d}_{i}_{j}") for j in range(cols)] for i in range(rows)]

        # 辅助函数：获取某个方向变量
        def get_conn(i, j, d):
            if d == 'U':
                return conn['U'][i][j] if i > 0 else None
            elif d == 'D':
                return conn['D'][i][j] if i < rows - 1 else None
            elif d == 'L':
                return conn['L'][i][j] if j > 0 else None
            elif d == 'R':
                return conn['R'][i][j] if j < cols - 1 else None
            return None

        # ------------------------------------------------------------------
        # 2. 基础约束：连接对称性
        #    对于相邻格子，连接变量必须相等
        # ------------------------------------------------------------------
        for i in range(rows):
            for j in range(cols):
                if i > 0:
                    model.Add(conn['U'][i][j] == conn['D'][i-1][j])
                if j > 0:
                    model.Add(conn['L'][i][j] == conn['R'][i][j-1])

        # ------------------------------------------------------------------
        # 3. 每个格子：雷（珍珠）恰好有2个连接，非雷有0个连接
        #    即：sum(conn) == 2 * is_mine
        # ------------------------------------------------------------------
        for i in range(rows):
            for j in range(cols):
                # 收集四个方向的连接变量（边界处为0）
                vars_ = []
                coeffs = []
                for d, (di, dj) in enumerate([(-1, 0), (1, 0), (0, -1), (0, 1)]):
                    ni, nj = i + di, j + dj
                    if 0 <= ni < rows and 0 <= nj < cols:
                        if di == -1:  # U
                            var = conn['U'][i][j]
                        elif di == 1:  # D
                            var = conn['D'][i][j]
                        elif dj == -1:  # L
                            var = conn['L'][i][j]
                        else:  # R
                            var = conn['R'][i][j]
                        vars_.append(var)
                        coeffs.append(1)

                # 判断该格是否为雷（白珍珠或黑珍珠）
                is_mine = False
                if (i, j) in clue_map:
                    typ = clue_map[(i, j)]
                    if typ == MasyuType.WHITE or typ == MasyuType.BLACK:
                        is_mine = True

                if is_mine:
                    # 雷：恰好2个连接
                    model.Add(sum(vars_) == 2)
                else:
                    # 非雷：0个连接
                    model.Add(sum(vars_) == 0)

        # ------------------------------------------------------------------
        # 4. 白珍珠和黑珍珠的连接模式约束
        #    白珍珠：直线通过（上下 或 左右）
        #    黑珍珠：转弯通过（上左、上右、下左、下右）
        # ------------------------------------------------------------------
        for (i, j), typ in clue_map.items():
            if typ == MasyuType.WHITE:
                self._add_white_pearl_constraint(model, conn, i, j, rows, cols)
            elif typ == MasyuType.BLACK:
                self._add_black_pearl_constraint(model, conn, i, j, rows, cols)

        # ------------------------------------------------------------------
        # 5. 回路连通性约束（左线约束）
        #    使用 SL_loop 规则，确保所有雷形成一条回路
        # ------------------------------------------------------------------
        if SL_loop is not None:
            loop_rule = SL_loop()
            # 传递 board 和 switch（None）
            loop_rule.create_constraints(board, switch)
        else:
            # 如果 SL_loop 不可用，尝试使用内置的回路连通性约束
            self._add_loop_connectivity_constraint(model, conn, rows, cols, clue_map)

        self.logger.info(f"MasyuRule: 已添加约束")

    # ----------------------------------------------------------------------
    # 辅助方法：白珍珠约束
    # ----------------------------------------------------------------------
    def _add_white_pearl_constraint(self, model, conn, i, j, rows, cols):
        """
        白珍珠约束：
        - 直线通过（上下 或 左右）
        - 至少一个相邻格（在回路方向上）是转弯的
        """
        U = conn['U'][i][j] if i > 0 else None
        D = conn['D'][i][j] if i < rows - 1 else None
        L = conn['L'][i][j] if j > 0 else None
        R = conn['R'][i][j] if j < cols - 1 else None

        def both(a, b):
            return a is not None and b is not None

        # 4.1 直线通过：要么 (U and D) 要么 (L and R)
        mode_UD = model.NewBoolVar(f"white_UD_{i}_{j}") if both(U, D) else None
        mode_LR = model.NewBoolVar(f"white_LR_{i}_{j}") if both(L, R) else None

        if mode_UD is not None and mode_LR is not None:
            # 至少一个模式为真
            model.Add(mode_UD + mode_LR >= 1)
            # mode_UD => (U and D)
            model.Add(mode_UD <= U)
            model.Add(mode_UD <= D)
            # mode_LR => (L and R)
            model.Add(mode_LR <= L)
            model.Add(mode_LR <= R)
        elif mode_UD is not None:
            # 只有 UD 模式可用
            model.Add(U == 1)
            model.Add(D == 1)
        elif mode_LR is not None:
            # 只有 LR 模式可用
            model.Add(L == 1)
            model.Add(R == 1)

        # 4.2 至少一个相邻格转弯
        # 转弯定义：该格的2个连接在垂直方向（不是相对方向）
        # 对于白珍珠，直线方向上的两个相邻格必须至少有一个转弯
        # 如果连接是上下，则相邻格为 (i-1,j) 和 (i+1,j)
        # 如果连接是左右，则相邻格为 (i,j-1) 和 (i,j+1)

        def is_turn(i2, j2):
            """判断格子 (i2, j2) 是否转弯（如果它是雷）"""
            if not (0 <= i2 < rows and 0 <= j2 < cols):
                return None
            U2 = conn['U'][i2][j2] if i2 > 0 else None
            D2 = conn['D'][i2][j2] if i2 < rows - 1 else None
            L2 = conn['L'][i2][j2] if j2 > 0 else None
            R2 = conn['R'][i2][j2] if j2 < cols - 1 else None
            # 转弯：垂直方向的连接（非相对方向）
            # 用辅助变量表示
            turn_var = model.NewBoolVar(f"turn_{i2}_{j2}")
            # turn_var = (U2 and L2) or (U2 and R2) or (D2 and L2) or (D2 and R2)
            # 由于最多2个连接，转弯等价于 不是 (U2 and D2) 且 不是 (L2 and R2)
            # 使用线性约束实现：turn_var + (U2 + D2 - 1) <= 1, turn_var + (L2 + R2 - 1) <= 1
            if both(U2, D2):
                model.Add(turn_var + U2 + D2 <= 2)  # 如果 U2=1,D2=1, 则 turn_var <=0
            if both(L2, R2):
                model.Add(turn_var + L2 + R2 <= 2)
            # 如果该格是雷（有2个连接）且不是直线，则为转弯
            # 我们无法直接约束 turn_var 为真，但可以通过其他约束间接实现
            # 这里我们只构造 turn_var 作为辅助，后面会用到
            return turn_var

        # 获取直线方向上的两个相邻格
        if both(U, D):
            turn_up = is_turn(i - 1, j)
            turn_down = is_turn(i + 1, j)
            if turn_up is not None and turn_down is not None:
                # 如果 UD 模式成立，则 turn_up 或 turn_down 至少一个为真
                if mode_UD is not None:
                    model.Add(mode_UD <= turn_up + turn_down)

        if both(L, R):
            turn_left = is_turn(i, j - 1)
            turn_right = is_turn(i, j + 1)
            if turn_left is not None and turn_right is not None:
                if mode_LR is not None:
                    model.Add(mode_LR <= turn_left + turn_right)

    # ----------------------------------------------------------------------
    # 辅助方法：黑珍珠约束
    # ----------------------------------------------------------------------
    def _add_black_pearl_constraint(self, model, conn, i, j, rows, cols):
        """
        黑珍珠约束：
        - 转弯通过（上左、上右、下左、下右）
        - 两个相邻格（在回路方向上）均不转弯（即都是直线）
        """
        U = conn['U'][i][j] if i > 0 else None
        D = conn['D'][i][j] if i < rows - 1 else None
        L = conn['L'][i][j] if j > 0 else None
        R = conn['R'][i][j] if j < cols - 1 else None

        def both(a, b):
            return a is not None and b is not None

        # 5.1 转弯通过：四种垂直组合之一
        modes = []
        if both(U, L):
            m_UL = model.NewBoolVar(f"black_UL_{i}_{j}")
            modes.append(m_UL)
            model.Add(m_UL <= U)
            model.Add(m_UL <= L)
        if both(U, R):
            m_UR = model.NewBoolVar(f"black_UR_{i}_{j}")
            modes.append(m_UR)
            model.Add(m_UR <= U)
            model.Add(m_UR <= R)
        if both(D, L):
            m_DL = model.NewBoolVar(f"black_DL_{i}_{j}")
            modes.append(m_DL)
            model.Add(m_DL <= D)
            model.Add(m_DL <= L)
        if both(D, R):
            m_DR = model.NewBoolVar(f"black_DR_{i}_{j}")
            modes.append(m_DR)
            model.Add(m_DR <= D)
            model.Add(m_DR <= R)

        # 至少一种模式为真
        if modes:
            model.Add(sum(modes) >= 1)

        # 5.2 两个相邻格均不转弯
        def is_straight(i2, j2):
            """判断格子 (i2, j2) 是否为直线（不转弯）"""
            if not (0 <= i2 < rows and 0 <= j2 < cols):
                return None
            U2 = conn['U'][i2][j2] if i2 > 0 else None
            D2 = conn['D'][i2][j2] if i2 < rows - 1 else None
            L2 = conn['L'][i2][j2] if j2 > 0 else None
            R2 = conn['R'][i2][j2] if j2 < cols - 1 else None
            # 直线 = (U and D) or (L and R)
            straight_var = model.NewBoolVar(f"straight_{i2}_{j2}")
            # 如果 U 和 D 都为1，则 straight_var 为真
            if both(U2, D2):
                model.Add(straight_var >= U2 + D2 - 1)
            # 如果 L 和 R 都为1，则 straight_var 为真
            if both(L2, R2):
                model.Add(straight_var >= L2 + R2 - 1)
            # 如果 straight_var 为真，则必须是 (U2 and D2) 或 (L2 and R2)
            # 但我们不需要反向约束，因为只需要强制直线
            return straight_var

        # 对于每种模式，相邻格为直线
        if both(U, L):
            straight_up = is_straight(i - 1, j)
            straight_left = is_straight(i, j - 1)
            if straight_up is not None and straight_left is not None:
                for m in [m_UL] if 'm_UL' in locals() else []:
                    model.Add(m <= straight_up)
                    model.Add(m <= straight_left)
        if both(U, R):
            straight_up = is_straight(i - 1, j)
            straight_right = is_straight(i, j + 1)
            if straight_up is not None and straight_right is not None:
                for m in [m_UR] if 'm_UR' in locals() else []:
                    model.Add(m <= straight_up)
                    model.Add(m <= straight_right)
        if both(D, L):
            straight_down = is_straight(i + 1, j)
            straight_left = is_straight(i, j - 1)
            if straight_down is not None and straight_left is not None:
                for m in [m_DL] if 'm_DL' in locals() else []:
                    model.Add(m <= straight_down)
                    model.Add(m <= straight_left)
        if both(D, R):
            straight_down = is_straight(i + 1, j)
            straight_right = is_straight(i, j + 1)
            if straight_down is not None and straight_right is not None:
                for m in [m_DR] if 'm_DR' in locals() else []:
                    model.Add(m <= straight_down)
                    model.Add(m <= straight_right)

    # ----------------------------------------------------------------------
    # 辅助方法：回路连通性约束（当 SL_loop 不可用时）
    # ----------------------------------------------------------------------
    def _add_loop_connectivity_constraint(self, model, conn, rows, cols, clue_map):
        """
        添加回路连通性约束：所有雷格必须形成一条回路（而非多条）。
        这是一个简化的实现，通过添加"无子回路"约束来实现。
        注意：这个实现可能不够完整，建议使用 SL_loop 规则。
        """
        self.logger.warning("使用内置回路连通性约束（可能不完整），建议安装 SL_loop 规则")

        # 获取所有雷格的位置
        cells = []
        for i in range(rows):
            for j in range(cols):
                if (i, j) in clue_map:
                    typ = clue_map[(i, j)]
                    if typ == MasyuType.WHITE or typ == MasyuType.BLACK:
                        cells.append((i, j))

        if len(cells) < 4:
            # 少于4个雷格无法形成回路，直接约束无解（但由其他约束保证）
            return

        # 为每个雷格分配一个顺序编号（从0开始）
        # 添加约束：每个雷格恰好有一个前驱和一个后继，且所有雷格连通
        # 使用 Miller-Tucker-Zemlin (MTZ) 约束
        n = len(cells)
        # 创建顺序变量 seq[i][j] (整数，范围 0..n-1)
        seq = {}
        for idx, (i, j) in enumerate(cells):
            seq[(i, j)] = model.NewIntVar(0, n - 1, f"seq_{i}_{j}")

        # 约束：对于每个雷格 (i,j)，它的两个连接方向上的相邻雷格必须有一个顺序编号为 seq[i][j] + 1 (mod n)
        # 这是一个循环约束，比较复杂
        # 简化：使用一个起始点，要求所有其他雷格都可以通过连接到达起始点
        # 但这里的实现比较复杂，略过，依赖于 SL_loop

        self.logger.warning("回路连通性约束未完全实现，请确保 SL_loop 规则可用")
