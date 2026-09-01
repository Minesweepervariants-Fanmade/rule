# -*- coding: utf-8 -*-
import datetime
import hashlib
import inspect
import sys
from typing import Optional, List, Tuple

from minesweepervariants.abs.Rrule import AbstractClueRule, AbstractClueValue
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.Mrule import AbstractMinesClueRule
from minesweepervariants.abs.rule import AbstractRule
from minesweepervariants.board import Board
from minesweepervariants.impl.impl_obj import get_rule
from minesweepervariants.impl.summon.solver import Switch
from minesweepervariants.utils.tool import get_random, get_logger

TODAY_RULE_ID: str = "2Z^"
TODAY_DATE = "2026-09-02"


def hash_str(input_str: str) -> str:
    return hashlib.md5(input_str.encode("utf-8")).hexdigest()[:4]


class UN(AbstractMinesRule):
    """
    隐藏左线规则 - 每个 2x2 子矩阵中的雷数不为 3。
    """

    id = "UN"

    name = "Unknown"
    name.zh_CN = "未知"
    doc = "Unknown"
    doc.zh_CN = ("每日00:00(UTC+8)随机选择一个左/右线规则 需要通过出题/猜测来判断到底是什么规则 "
                 "当传入空值参数的时候将会抛出异常并输出当前的规则具体内容 当传入'r'的时候将会重新随机一个规则")
    author = ("雾", 3140864122)
    tags = ["Local", "Strict Shape"]
    lib_only = False
    creation_time = "2026-07-20"

    def __init__(self, board=None, data=None):
        """初始化规则，存储 data 参数。"""
        global TODAY_DATE
        super().__init__(board, data)
        today_date = datetime.date.today().isoformat()
        if data in ["r"] or (today_date != TODAY_DATE):
            data = "r"
        elif data == "":
            raise ValueError(
                f"实际规则为:[{TODAY_RULE_ID}](hash:{hash_str(TODAY_RULE_ID)})"
            )
        if data is not None:
            result = self.rand_choose_rule(board, None if data == "r" else data)
            self.replace_rule(**result)

        self.rule: AbstractRule = get_rule(TODAY_RULE_ID)(board, None)

    def get_name(self) -> str:
        return f"{self.id}:{hash_str(TODAY_RULE_ID)}"

    def rand_choose_rule(self, board: Board, specify_rule: Optional[str] = None):
        global TODAY_RULE_ID
        random = get_random()

        def get_all_subclasses(cls):
            subclasses = set(cls.__subclasses__())
            for subclass in list(subclasses):
                subclasses.update(get_all_subclasses(subclass))
            return subclasses

        rule_list = list(get_all_subclasses(AbstractRule))
        random.shuffle(rule_list)
        for rule_cls in rule_list:
            if issubclass(rule_cls, AbstractMinesClueRule):
                continue
            _board = board.clone()
            if not hasattr(rule_cls, "id"):
                continue
            if specify_rule is not None and rule_cls.id != specify_rule:
                continue
            try:
                rule = rule_cls(_board, None)
            except Exception:
                continue
            if len(_board.get_board_keys()) > 1:
                continue
            TODAY_RULE_ID = rule.id
            rule_line = "M" if isinstance(rule, AbstractMinesClueRule) else (
                "L" if isinstance(rule, AbstractMinesRule) else "R"
            )
            lib_only = rule.lib_only
            self.lib_only = lib_only
            return {"rule_line": rule_line, "lib_only": lib_only}
        raise ValueError("未找到符合的规则")

    def replace_rule(self, rule_line, lib_only):
        """根据规则类型，直接整行替换源文件中的 TODAY_RULE_ID、TODAY_DATE 和类继承。"""
        global TODAY_DATE
        logger = get_logger()

        new_rule_id = TODAY_RULE_ID
        new_date = datetime.date.today().isoformat()

        if rule_line == 'M':
            base_class = 'AbstractMinesClueRule'
        elif rule_line == 'L':
            base_class = 'AbstractMinesRule'
        elif rule_line == 'R':
            base_class = 'AbstractClueRule'
        else:
            raise ValueError(f"未知的规则线{rule_line}")

        module_file = inspect.getfile(sys.modules[self.__module__])

        with open(module_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        found_rule_id = False
        found_date = False
        found_class = False
        found_lib_only = False

        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith('TODAY_RULE_ID') and not found_rule_id:
                old_line = line.rstrip('\n')
                new_line = f'TODAY_RULE_ID: str = "{new_rule_id}"'
                new_lines.append(new_line + '\n')
                found_rule_id = True
                logger.info(f"替换 TODAY_RULE_ID: 旧行 '{old_line}' -> 新行 '{new_line}'")
            elif stripped.startswith('TODAY_DATE') and not found_date:
                old_line = line.rstrip('\n')
                new_line = f'TODAY_DATE = "{new_date}"'
                new_lines.append(new_line + '\n')
                found_date = True
                logger.info(f"替换 TODAY_DATE: 旧行 '{old_line}' -> 新行 '{new_line}'")
            elif stripped.startswith('class UN(') and not found_class:
                old_line = line.rstrip('\n')
                new_line = f'class UN({base_class}):'
                new_lines.append(new_line + '\n')
                found_class = True
                logger.info(f"替换 class UN: 旧行 '{old_line}' -> 新行 '{new_line}'")
            elif stripped.startswith('lib_only = ') and not found_lib_only:
                old_line = line.rstrip('\n')
                new_line = line.split("lib_only = ")[0] + "lib_only = " + str(lib_only)
                new_lines.append(new_line + '\n')
                found_lib_only = True
                logger.info(f"替换 lib_only: 旧行 '{old_line}' -> 新行 '{new_line}'")
            else:
                new_lines.append(line)

        if not found_rule_id:
            logger.warning("未找到 TODAY_RULE_ID 行，未替换")
        if not found_date:
            logger.warning("未找到 TODAY_DATE 行，未替换")
        if not found_class:
            logger.warning("未找到 class UN 行，未替换")
        if not found_lib_only:
            logger.warning("未找到 lib_only 行，未替换")

        with open(module_file, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        TODAY_DATE = new_date
        raise ValueError(f"随机抽取了一个规则(hash:{hash_str(TODAY_RULE_ID)})")

    def fill(self, board: 'Board') -> 'Board':
        if hasattr(self.rule, "fill"):
            fill_fn = getattr(self.rule, "fill")
            return fill_fn(board)
        return board

    def create_constraints(self, board: 'Board', switch) -> None:
        fake_switch = FakeSwitch(switch, self)
        return self.rule.create_constraints(board, fake_switch)

    def suggest_total(self, info: dict) -> None:
        return self.rule.suggest_total(info)

    def init_board(self, board: 'Board') -> None:
        return self.rule.init_board(board)

    def init_clear(self, board: 'Board') -> None:
        return self.rule.init_clear(board)

    def combine(self, rules: List[Tuple['AbstractRule', Optional[str]]]) -> None:
        return self.rule.combine(rules)

    def onboard_init(self, board: 'Board') -> None:
        return self.rule.onboard_init(board)

    def get_deps(self) -> List[str]:
        return self.rule.get_deps()

    def companion_id(self) -> str:
        return self.rule.companion_id()

    def companion_data(self) -> str:
        return self.rule.companion_data()


class FakeSwitch(Switch):
    def __init__(self, switch, rule) -> None:
        self.switch = switch
        self.rule = rule
        super().__init__()

    def get(self, model, obj, index=None):
        if isinstance(obj, AbstractRule):
            obj = self.rule
        return self.switch.get(model, obj, index)
