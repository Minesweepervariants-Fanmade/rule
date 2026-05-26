from ....abs.board import AbstractBoard
from ....abs.Lrule import AbstractMinesRule


def parse(s: str, width: int, height: int) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    result = []
    result_not = []
    idx = -1
    for idx, chr in enumerate(filter(lambda c: c in "01Xx", s)):
        row, col = idx // width, idx % width
        if chr.upper() == "X":
            continue
        elif chr == "0":
            result_not.append((row, col))
        elif chr == "1":
            result.append((row, col))
    if idx + 1 != width * height:
        raise ValueError(f"Data length {idx + 1} does not match board size {width * height}.")

    return result, result_not

class RuleFORCE(AbstractMinesRule):
    id = "FORCE"
    name = "FORCE"
    name.zh_CN = "强制雷排布"
    doc = "The parameter specifies the mine placement matrix. 0, 1, and X represent non-mine, mine, and uncertain respectively."
    doc.zh_CN = "参数指定雷排布矩阵. 0 1 X分别表示非雷、雷和不确定."
    author = ("NT", 2201963934)

    tags = ["Creative", "Local", "Parameter"]
    creation_time = "2026-05-25"

    def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
        super().__init__(board, data)
        self.values = []
        self.values_not = []
        if data is None:
            raise ValueError("Data is required for FORCE rule.")

        width = board.boundary(board.get_interactive_keys()[0]).col + 1
        height = board.boundary(board.get_interactive_keys()[0]).row + 1

        self.values, self.values_not = parse(data, width, height)
        print(f"Parsed FORCE rule: {len(self.values)} mines, {(self.values_not)} non-mines.")

    def create_constraints(self, board, switch):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():
            for pos in self.values:
                model.Add(board.get_variable(board.get_pos(*pos, key)) == 1).OnlyEnforceIf(s)
            for pos in self.values_not:
                model.Add(board.get_variable(board.get_pos(*pos, key)) == 0).OnlyEnforceIf(s)
