from __future__ import annotations

from typing import TYPE_CHECKING


from minesweepervariants.utils.impl_obj import MINES_TAG, VALUE_QUESS

from ....abs.Lrule import AbstractMinesRule
from ....utils.tool import get_random

if TYPE_CHECKING:
  from minesweepervariants.board import Board, Position
  from ....impl.summon.solver import Switch


class RuleTWpp(AbstractMinesRule):
  id = "TW''"
  name = "Twin''"
  name.zh_CN = "双胞胎"  # pyright: ignore[reportAttributeAccessIssue]
  doc = "The gray number on the board indicates that if that cell is a mine, it represents the number of mines around the corresponding cell on the opposite board. "
  doc.zh_CN = "两个主板，灰色数表示该格如果为雷则表示对面周围八个雷数。"  # pyright: ignore[reportAttributeAccessIssue]
  author = ("NT", 2201963934)
  tags = ["Creative", "Global"]
  creation_time = "2026-05-30"

  def __init__(self, board: "Board", data: str | None = None) -> None:
    super().__init__(board, data)
    if data is not None:
      try:
        self.seed = int(data)
      except (TypeError, ValueError):
        pass
    self._count_cache: dict[tuple[str, int, int], int] = {}

    key = board.get_interactive_keys()[0]
    boundary_pos = board.boundary(key=key)
    rows, cols = boundary_pos.row + 1, boundary_pos.col + 1
    board.generate_board("TW''", Size(cols, rows))
    board.set_config("TW''", "interactive", True)
    board.set_config("TW''", "row_col", True)
    board.set_config("TW''", "VALUE", VALUE_QUESS)
    board.set_config("TW''", "MINES", MINES_TAG)
    self.onboard_init(board)

  def _populate_count_cache(self, board: "Board", key: str):
    random = get_random()
    positions = sorted((pos for pos, _ in board(key=key)), key=lambda p: (p.row, p.col))

    boundary_pos = board.boundary(key=key)
    row, col = boundary_pos.row + 1, boundary_pos.col + 1

    for pos in positions:
      cache_key = (pos.board_key, pos.row, pos.col)
      if cache_key not in self._count_cache:
        self._count_cache[cache_key] = random.randint(0, self._ub(pos, row, col))

  def is_bound(self, pos: "Position", row: int, col: int) -> bool:
    return pos.row == 0 or pos.row == row - 1 or pos.col == 0 or pos.col == col - 1

  def is_corner(self, pos: "Position", row: int, col: int) -> bool:
    return pos.row == 0 and pos.col == 0 or \
           pos.row == 0 and pos.col == col - 1 or \
           pos.row == row - 1 and pos.col == 0 or \
           pos.row == row - 1 and pos.col == col - 1

  def _ub(self, pos: "Position", row: int, col: int) -> int:
    if self.is_corner(pos, row, col):
      return 3
    elif self.is_bound(pos, row, col):
      return 5
    else:
      return 8

  def _mine_count(self, pos: "Position") -> int:
    key = (pos.board_key, pos.row, pos.col)
    return self._count_cache[key]

  def onboard_init(self, board: "Board"):
    # 方向在初始化阶段一次性写入缓存, 显示与约束统一读取同一映射。
    self._populate_count_cache(board, key=board.get_interactive_keys()[0])
    self._populate_count_cache(board, key="TW''")
    self._apply_pos_labels(board, key=board.get_interactive_keys()[0])
    self._apply_pos_labels(board, key="TW''")

  def _apply_pos_labels(self, board: "Board", key: str):
    labels = {}
    for pos, _ in board(key=key):
      mine_count = self._mine_count(pos)
      labels[pos] = str(mine_count)
    board.set_config(key, "labels", labels)
    board.set_config(key, "pos_label", True)


  def create_constraints(self, board: "Board", switch: "Switch"):
    model = board.get_model()
    s = switch.get(model, self)

    key_main = board.get_interactive_keys()[0]
    for key1, key2 in [(key_main, "TW''"), ("TW''", key_main)]:
      for pos, var in board(key=key1, mode="variable"):
        mine_count = self._mine_count(pos)
        pos.board_key = key2
        # 如果该格是雷，则周围雷数为mine_count
        neighbors = pos.neighbors(2)
        model.add(sum(v for n in neighbors if (v:=board.get_variable(n)) is not None) == mine_count).OnlyEnforceIf([var,s])