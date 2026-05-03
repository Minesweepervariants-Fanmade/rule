"""
[3MA] 三雷区：题板正好有三个四连通雷区。

规则拆分定义(验收基准):
1) 规则对象与适用范围:
    - 左线规则(Lrule)。
    - 约束对象是当前 interactive key 内所有有效格的 raw 状态。
    - 统计对象仅为雷格(raw=1)在四连通意义下形成的连通区域数量。

2) 核心术语精确定义:
    - 四连通: 仅以上下左右作为相邻关系，不包含对角相邻。
    - 雷区域数量: 当前 key 内，raw=1 的极大四连通分量个数。

3) 计数对象、边界条件、越界处理:
    - 仅统计 board(key=当前 key) 可枚举到、且 raw 变量非空的有效格。
    - 越界格、洞格、非有效交互格不参与区域构成，也不作为连通路径。
    - 若当前 key 无雷，则雷区域数量为 0。

4) 参数语义:
    - data 为 None 或空字符串时，默认约束为雷区域数量 == 3。
    - data 为比较串时，支持区间子句: "1..2", "..5", "1.."，其中 `..` 表示左右端点都包含。
    - 为兼容历史，也支持旧比较子句: ">3", ">=2", "<5", "<=4", "!=3"。
    - 多子句以逗号分隔，语义为 AND，例如 "1..,!=3"。
    - 参数仅影响雷区域数量约束，不改变四连通定义与计数对象。

5) create_constraints 约束语义:
    - 必须复用 connect 建模四连通雷连通块。
    - 必须把雷区域数量与默认/参数化条件精确等价编码，不可只编码必要条件。

6) 可验证样例:
    - 样例A(默认应通过): 一个 5x5 盘面中恰有 3 个相互四不连通的雷块，则满足默认规则。
    - 样例B(参数应失败): 若 data 为 ">=4"，但盘面仅有 3 个四连通雷块，则应判定不满足。
"""

from ....abs.Lrule import AbstractMinesRule
import re

from .connect import connect


class Rule3MA(AbstractMinesRule):
    id = "3MA"
    name = "Triple Mines Areas"
    name.zh_CN = "三雷区"
    doc = "The board has exactly three four-connected mine areas"
    doc.zh_CN = "题板正好有三个四连通雷区"
    author = ("NT", 2201963934)
    tags = ["Creative", "Global", "Connectivity", "Parameter"]

    _COMPARATOR_RE = re.compile(r"^(>=|<=|!=|>|<)\s*(-?\d+)$")

    def __init__(self, board=None, data=None) -> None:
        super().__init__(board, data)
        self.component_conditions: list[tuple[str, int]] = self._parse_data(data)

    @staticmethod
    def _parse_int(text: str, raw_data: str) -> int:
        try:
            return int(text)
        except ValueError as exc:
            raise ValueError(f"3MA data 数值非法: {raw_data!r}") from exc

    @classmethod
    def _parse_interval_clause(cls, item: str, raw_data: str) -> list[tuple[str, int]] | None:
        if ".." not in item:
            return None

        left, right = item.split("..", 1)
        left = left.strip()
        right = right.strip()

        if not left and not right:
            raise ValueError(f"3MA data 区间子句不能为空: {raw_data!r}")

        conditions: list[tuple[str, int]] = []
        lower = None
        upper = None

        if left:
            lower = cls._parse_int(left, raw_data)
            conditions.append((">=", lower))

        if right:
            upper = cls._parse_int(right, raw_data)
            conditions.append(("<=", upper))

        if lower is not None and upper is not None and lower > upper:
            raise ValueError(f"3MA data 区间上下界非法: {raw_data!r}")

        return conditions

    @classmethod
    def _parse_data(cls, data) -> list[tuple[str, int]]:
        if data is None:
            return []

        if not isinstance(data, str):
            raise ValueError(f"3MA data 必须是比较字符串, 但收到: {data!r}")

        text = data.strip()
        if not text:
            return []

        conditions: list[tuple[str, int]] = []
        for part in text.split(","):
            item = part.strip()
            if not item:
                raise ValueError(f"3MA data 中存在空比较子句: {data!r}")

            interval_conditions = cls._parse_interval_clause(item, data)
            if interval_conditions is not None:
                conditions.extend(interval_conditions)
                continue

            match = cls._COMPARATOR_RE.fullmatch(item)
            if match is None:
                raise ValueError(f"3MA data 格式非法: {data!r}")

            conditions.append((match.group(1), int(match.group(2))))

        return conditions

    def create_constraints(self, board, switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            positions_vars = [
                (pos, board.get_variable(pos, special='raw'))
                for pos, _ in board(key=key, mode='variable', special='raw')
            ]
            if not positions_vars:
                continue

            n = len(positions_vars)
            root_vars = [model.NewBoolVar(f"3ma_root_{key}_{i}") for i in range(n)]
            component_count = model.NewIntVar(0, n, f"3ma_component_count_{key}")

            connect(
                model=model,
                board=board,
                switch=s,
                component_num=component_count,
                connect_value=1,
                nei_value=1,
                root_vars=root_vars,
                positions_vars=positions_vars,
                special='raw',
            )

            if not self.component_conditions:
                model.Add(component_count == 3).OnlyEnforceIf(s)
                continue

            for op, value in self.component_conditions:
                if op == ">":
                    model.Add(component_count > value).OnlyEnforceIf(s)
                elif op == ">=":
                    model.Add(component_count >= value).OnlyEnforceIf(s)
                elif op == "<":
                    model.Add(component_count < value).OnlyEnforceIf(s)
                elif op == "<=":
                    model.Add(component_count <= value).OnlyEnforceIf(s)
                elif op == "!=":
                    model.Add(component_count != value).OnlyEnforceIf(s)
                else:
                    raise ValueError(f"3MA 不支持的比较符号: {op!r}")
