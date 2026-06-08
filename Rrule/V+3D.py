from typing import TYPE_CHECKING

from ....abs.Rrule import AbstractClueRule, AbstractClueValue
from typing import cast
from minesweepervariants.abs.rule import AbstractValue
from minesweepervariants.json_object import deep_unwrap
from minesweepervariants.utils.value_template import is_value_template, Template, SingleIntValue
from minesweepervariants.board import JSONObject, Board, Position

if TYPE_CHECKING:
   from ortools.sat.python.cp_model import IntVar


class RuleVPlus3D(AbstractClueRule):
   id = "V+3D"
   name = "V+3D"
   name.zh_CN = "V+辞典（第n空格+周围雷数）"
   doc = "Clue value equals n + number of mines around the n-th empty neighbor"
   doc.zh_CN = "第n格空格周围有m个雷，则线索值等于 n + m"
   author = ("NT", 2201963934)
   tags = ["Creative", "Local", "Number Clue"]
   creation_time = "2026-05-24"

   def __init__(self, board: 'Board' = None, data=None) -> None:
      super().__init__(board, data)

   @staticmethod
   def _empty_neighbors(board: 'Board', pos: 'Position') -> list['Position']:
      # 空格定义：非雷格（只要不是 'F' 都算）
      result: list[Position] = []
      for nei in pos.neighbors(2):
         if not board.in_bounds(nei):
            continue
         if board.get_type(nei) == 'F':
            continue
         result.append(nei)
      return result

   def fill(self, board: 'Board') -> 'Board':
      # 按用户要求的算法：遍历整张题板，记录到达每个格时遇到的非雷格数量 an（只要不是 'F' 都算）
      # 然后为每个非雷格赋值：count = an + 周围八格雷数
      for key in board.get_interactive_keys():
         an_counter = 0
         for pos, _ in board(key=key):
            # 只为非雷格设置线索值
            if board.get_type(pos) == 'F':
               continue

            # an = 到达当前格时遇到的非雷格数量（包含自身）
            an = an_counter + 1

            # 计算当前格周围的雷数
            m = 0
            for q in pos.neighbors(2):
               if not board.in_bounds(q):
                  continue
               if board.get_type(q) == 'F':
                  m += 1

            # 按用户最新要求：只在 Value 中存储 S = n + 周围雷数 = an + m
            S = an + m
            board.set_value(pos, ValueV3D(pos, value=S))

            an_counter += 1
      return board



class ValueV3D(AbstractClueValue):
   id = RuleVPlus3D.id
   def __init__(self, pos: 'Position', code: bytes = None, value: int = 0):
      super().__init__(pos, code if code is not None else b"")
      # 仅保存合并值 S = n + m
      if code is not None and len(code) >= 1:
         self.value = code[0]
      else:
         self.value = value
      self.neighbor = self.pos.neighbors(2)

   def __repr__(self):
      return f"{self.value}"

   @classmethod
   def type(cls) -> bytes:
      return RuleVPlus3D.id.encode("ascii")

   def code(self) -> bytes:
      # 只编码合并值 S
      return bytes([self.value])

   def high_light(self, board: 'Board') -> list['Position']:
      return [nei for nei in self.neighbor if board.in_bounds(nei)]

   def create_constraints(self, board: 'Board', switch):
         model = board.get_model()
         s = switch.get(model, self.pos)
         # 全盘遍历以重现 fill 的 an 顺序
         positions = []
         for key in board.get_interactive_keys():
            for p, _ in board(key=key):
               positions.append(p)
         is_mine_vars = [board.get_variable(p) for p in positions]
         # 把 None 替换为常量 0，避免把 None 传入 sum()
         is_mine_vars = [v if v is not None else model.NewConstant(0) for v in is_mine_vars]
         nonF = [model.NewIntVar(0, 1, f"V3D_nf_{i}_{self.pos.x}_{self.pos.y}") for i in range(len(is_mine_vars))]
         for i, v in enumerate(is_mine_vars):
            model.Add(nonF[i] + v == 1).OnlyEnforceIf(s)
         prefs = [model.NewIntVar(0, len(nonF), f"V3D_p_{i}_{self.pos.x}_{self.pos.y}") for i in range(len(nonF))]
         for i in range(len(nonF)):
            model.Add(prefs[i] == sum(nonF[: i + 1])).OnlyEnforceIf(s)
         # 当前格在全盘遍历中的索引，与 fill 中的 an 对应
         idx = positions.index(self.pos)
         around = board.batch(self.pos.neighbors(2), mode="variable", drop_none=True)
         a_sum = sum(around) if around else 0
         model.Add(prefs[idx] + a_sum == self.value).OnlyEnforceIf(s)
