import re
from typing import Tuple, List, Any

from ....abs.board import AbstractBoard, AbstractPosition, MASTER_BOARD
from ....abs.Lrule import AbstractMinesRule

import re
import base64


def _parse_binary_string(bin_str: str, bound: "AbstractPosition"):
    """
    根据二进制串（仅含 '0'/'1'）填充 result 与 result_not。
    按行优先顺序遍历，二进制串长度可以小于等于总单元格数。
    如果某一位置超出范围且该位为 '1'，则抛出异常；
    如果为 '0'，则忽略超出部分。
    """
    result = []
    result_not = []
    for idx, ch in enumerate(bin_str):
        y = idx // (bound.col + 1)
        x = idx % (bound.col + 1)

        # 检查是否超出范围
        if y > bound.row or x > bound.col:
            if ch == '1':
                raise ValueError(f"Position out of bound at index {idx} (row={y}, col={x}), but bit is '1'")
            continue

        if ch == '1':
            result.append((y, x))
        else:
            result_not.append((y, x))

    return result, result_not


def parse(s: str, bound: "AbstractPosition") -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    total_cells = (bound.row + 1) * (bound.col + 1)

    # ----- 1. 尝试纯 01 串（仅含 '0'/'1'）-----
    if set(s) <= {'0', '1'}:
        return _parse_binary_string(s, bound)

    # ----- 2. 尝试十六进制串（0-9A-Fa-f）-----
    if all(c in "0123456789ABCDEFabcdef" for c in s):
        # 将 hex 字符串转换为二进制串（每个 hex digit → 4 bits）
        bin_chars = []
        for ch in s:
            bin_chars.append(format(int(ch, 16), '04b'))
        bin_str = ''.join(bin_chars)
        return _parse_binary_string(bin_str, bound)

    # ----- 3. 尝试 Base64 串（解码后得到字节，再转为 01 串）-----
    # Base64 字符集：A-Z a-z 0-9 + / =，长度通常为 4 的倍数
    # 使用 strict 解码，失败则跳过
    try:
        # 标准 base64 解码，要求填充正确
        decoded_bytes = base64.b64decode(s, validate=True)
        # 将每个字节转为 8 位二进制，拼接成完整 01 串
        bin_str = ''.join(format(byte, '08b') for byte in decoded_bytes)
        return _parse_binary_string(bin_str, bound)
    except Exception:
        pass  # 解码失败，继续尝试其他格式

    # ----- 4. 原有单元格引用格式（如 "A1;~B2"）-----
    result = []
    result_not = []
    for part in s.split(";"):
        match = re.match(r'^(~)?([A-Z]+)(\d+)$', part)
        if match is None:
            raise ValueError(f"Invalid format: {part}")
        is_not, letters, number = match.groups()
        # 列号转换（0-based）
        x = sum((ord(c) - ord('A') + 1) * (26 ** i) for i, c in enumerate(reversed(letters))) - 1
        y = int(number) - 1
        if is_not == "~":
            result_not.append((y, x))
        else:
            result.append((y, x))
    return result, result_not


class RuleA2(AbstractMinesRule):
    id = "A2"
    name = "A2 is a mine"
    name.zh_CN = "A2 格是雷"
    doc = "A2 is a mine"
    doc.zh_CN = "参数;分割指定雷，前面加~表示非雷"
    author = ("NT", 2201963934)

    tags = ["Creative", "Local", "Parameter"]
    creation_time = "2025-09-10"

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        self.values = []
        self.values_not = []
        if data is None:
            self.values, self.values_not = [(1, 0)], []
            return

        self.values, self.values_not = parse(data, board.boundary())
        print(f"values: {[board.get_pos(*pos, MASTER_BOARD) for pos in self.values]}")
        print(f"values_not: {[board.get_pos(*pos, MASTER_BOARD) for pos in self.values_not]}")

    def create_constraints(self, board, switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            for pos in self.values:
                model.Add(board.get_variable(board.get_pos(*pos, key)) == 1).OnlyEnforceIf(s)
            for pos in self.values_not:
                model.Add(board.get_variable(board.get_pos(*pos, key)) == 0).OnlyEnforceIf(s)

    def suggest_total(self, info: dict[str, Any]) -> None:

        ub = info["total"][MASTER_BOARD]
        # info["soft_fn"](len(self.values), 8)

        def a(model, total):
            model.add(len(self.values) <= total)
            model.add(total <= (ub - len(self.values_not)))

        info["hard_fns"].append(a)
