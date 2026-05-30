from __future__ import annotations

from typing import TYPE_CHECKING

from ....abs.Lrule import AbstractMinesRule
from ....utils.tool import get_random

if TYPE_CHECKING:
  from ....abs.board import AbstractBoard, AbstractPosition
  from ....impl.summon.solver import Switch


class RuleTWp(AbstractMinesRule):
  id = "TW'"
  name = "Twin Chimera"
  name.zh_CN = "嵌合体"  # pyright: ignore[reportAttributeAccessIssue]
  doc = "The gray number on the board indicates that if that cell is a mine, it represents the number of mines around it. "
  doc.zh_CN = "主板灰色数表示该格如果为雷则表示自己周围八个雷数。"  # pyright: ignore[reportAttributeAccessIssue]
  author = ("NT", 2201963934)
  tags = ["Creative", "Global"]
  creation_time = "2026-05-30"

  def __init__(self, board: "AbstractBoard", data: str | None = None) -> None:
    super().__init__(board, data)
    if data is not None:
      try:
        self.seed = int(data)
      except (TypeError, ValueError):
        pass
    self._count_cache: dict[tuple[str, int, int], int] = {}
    self.onboard_init(board)

  def _populate_count_cache(self, board: "AbstractBoard", key: str):
    random = get_random()
    positions = sorted((pos for pos, _ in board(key=key)), key=lambda p: (p.row, p.col))

    boundary_pos = board.boundary(key=key)
    row, col = boundary_pos.row + 1, boundary_pos.col + 1

    for pos in positions:
      cache_key = (pos.board_key, pos.row, pos.col)
      if cache_key not in self._count_cache:
        self._count_cache[cache_key] = random.randint(0, self._ub(pos, row, col))

  def is_bound(self, pos: "AbstractPosition", row: int, col: int) -> bool:
    return pos.row == 0 or pos.row == row - 1 or pos.col == 0 or pos.col == col - 1

  def is_corner(self, pos: "AbstractPosition", row: int, col: int) -> bool:
    return pos.row == 0 and pos.col == 0 or \
           pos.row == 0 and pos.col == col - 1 or \
           pos.row == row - 1 and pos.col == 0 or \
           pos.row == row - 1 and pos.col == col - 1

  def _ub(self, pos: "AbstractPosition", row: int, col: int) -> int:
    if self.is_corner(pos, row, col):
      return 3
    elif self.is_bound(pos, row, col):
      return 5
    else:
      return 8

  def _mine_count(self, pos: "AbstractPosition") -> int:
    key = (pos.board_key, pos.row, pos.col)
    return self._count_cache[key]

  def onboard_init(self, board: "AbstractBoard"):
    # 方向在初始化阶段一次性写入缓存, 显示与约束统一读取同一映射。
    self._populate_count_cache(board, key=board.get_interactive_keys()[0])
    self._apply_pos_labels(board)

  def _apply_pos_labels(self, board: "AbstractBoard"):
    key = board.get_interactive_keys()[0]
    labels = {}
    for pos, _ in board(key=key):
      mine_count = self._mine_count(pos)
      labels[pos] = str(mine_count)
    board.set_config(key, "labels", labels)
    board.set_config(key, "pos_label", True)


  def create_constraints(self, board: "AbstractBoard", switch: "Switch"):
    model = board.get_model()
    s = switch.get(model, self)

    key = board.get_interactive_keys()[0]

    for pos, var in board(key=key, mode="variable"):
      mine_count = self._mine_count(pos)
      # 如果该格是雷，则周围雷数为mine_count
      neighbors = pos.neighbors(2)
      model.add(sum(v for n in neighbors if (v:=board.get_variable(n)) is not None) == mine_count).OnlyEnforceIf([var,s])