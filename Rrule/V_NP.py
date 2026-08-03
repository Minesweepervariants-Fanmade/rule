"""
[V_NP] 专为 NP' 配套的右线规则：每个数字标明周围八格内 NP' 雷值之和。
"""
from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.board import Board, Position
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.utils.value_template import SingleIntValue, Template
from minesweepervariants.json_object import deep_unwrap
from typing import Self, cast
from minesweepervariants.impl.rule.Lrule.np_utils import register_np_prime_type


class DataVNP(SingleIntValue):
    """NP' 配套线索的数据类"""
    def __init__(self, value: int, rule: str):
        super().__init__(value, False)
        self.rule: str = rule

    def _template(self) -> Template:
        result = super()._template()
        result["_SingleIntValue"] = True
        result["data"] = self.value
        result["rule"] = self.rule
        return result

    @classmethod
    def try_from(cls, data: Template) -> Self | None:
        if not data.get("_SingleIntValue", False):
            return None
        value = cast(int, data["data"])
        rule = cast(str, data["rule"])
        return cls(value, rule)


class RuleVNP(AbstractClueRule):
    id = "V_NP"
    name = "NP' Value"
    name.zh_CN = "负标值"
    doc = "Each number indicates the sum of NP' mine values in the surrounding eight cells"
    doc.zh_CN = "每个数字标明周围八格内 NP' 雷值之和"
    tags = ["Variant", "Local", "Number Clue", "Mine-Value"]
    creation_time = "2026-08-04"
    author = ("", 740652480)

    def __init__(self, board: "Board" = None, data=None) -> None:
        super().__init__(board, data)
        # data 应该是命名空间名称，如 'NP''
        self.rule = data or "NP'"

    def fill(self, board: 'Board') -> 'Board':
        """填充所有未定义格为 NP' 线索格"""
        # 确保 NP' 命名空间已注册（clear_board 可能清除了注册）
        register_np_prime_type(board)
        
        if not board.has_type_special(self.rule):
            from minesweepervariants.utils.tool import get_logger
            logger = get_logger()
            logger.error(f"未找到 {self.rule} 的命名域")
            raise ValueError(f"未在命名空间中找到 [{self.rule}]")

        for pos, _ in board("N", special='raw'):
            # 计算周围八格内 NP' 雷值之和
            total = 0
            for neighbor in pos.neighbors(2):
                if board.in_bounds(neighbor):
                    val = board.get_type(neighbor, special=self.rule)
                    if val is not None:
                        total += val
            board.set_value(pos, ValueVNP(pos, count=total, rule=self.rule))
        return board


class ValueVNP(AbstractClueValue):
    id = RuleVNP.id

    def __init__(self, pos: Position, count: int = 0, rule: str = "NP'", *args, **kwargs):
        super().__init__(pos, *args, **kwargs)
        self.rule = rule
        self.count = count
        self.pos = pos
        self.value: DataVNP = DataVNP(count, rule)

    @classmethod
    def from_json(cls, pos: Position, data):
        _data = deep_unwrap(data)
        from minesweepervariants.utils.value_template import is_value_template
        if not is_value_template(_data):
            raise TypeError("value is not template")
        template_data = cast(Template, _data)
        value_obj = DataVNP.try_from(template_data)
        if value_obj is None:
            raise ValueError("value is empty")
        return cls(pos, value_obj.value, value_obj.rule)

    def create_constraints(self, board: 'Board', switch: Switch):
        """创建 CP-SAT 约束：周围 NP' 雷值之和等于 count"""
        model = board.get_model()
        s = switch.get(model, self.pos)

        neighbor_vars = []
        for neighbor in self.pos.neighbors(2):
            if board.in_bounds(neighbor):
                var = board.get_variable(neighbor, special=self.rule)
                neighbor_vars.append(var)

        if neighbor_vars:
            model.Add(sum(neighbor_vars) == self.count).OnlyEnforceIf(s)
