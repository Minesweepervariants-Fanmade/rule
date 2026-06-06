from minesweepervariants.board import Board
from . import AbstractClueSharp

class Rule1L2sharp(AbstractClueSharp):
    id = "1L2#"
    name = "Liar + Label'"
    name.zh_CN = "误差 + 标签"
    doc = ("Includes the following rules: [1L], [1L2X], [1L2D], [1L2M], [1L2A]\n"
           "Use [1L2#:] to exclude [1L2A]")
    doc.zh_CN = ("包含以下规则: [1L], [1L2X], [1L2D], [1L2M], [1L2A]\n"
              "使用[1L2#:]以去除[1L2A]")
    tags = ["Original", "Local"]
    creation_time = "2025-08-30"
    author = ("", 0)

    def __init__(self, board: "Board" = None, data=None) -> None:
        rules_name = ["1L", "1L2X", "1L2D", "1L2M"]
        if data is None:
            rules_name += ["1L2A"]
        super().__init__(rules_name, board, data)
