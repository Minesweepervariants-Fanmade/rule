"""
规则拆分定义 - MRG (合并)
代办规则
名称:[MRG]
介绍: 合并：独立考察每一行, 考虑每个长度为4的小段(4n...4n+3), (最后部分不足4个则忽略)，若第4n+1格与4n+2格相同，则4n+3格也与之相同，否则4n+3格与4n格不同。其中n是自然数，首列为第0格。
作者:NT (2201963934)
最后编辑时间:2026-05-16 04:23:46

1) 规则对象与适用范围
- 对象: 雷格（每个格子是否为雷的布尔状态）。
- 适用范围: 左线规则（Lrule），对每一行独立生效。规则仅约束行内同一行的格子排列，不应引入跨列的全局计数约束。
- 影响域: 仅影响被规则作用的行（及框架默认的左线传播语义：在填表阶段可视为只针对当前行约束，解算器阶段使用等价约束表达）。

2) 核心术语精确定义
- 列索引以 0 开始。对于自然数 n，定义长度为 4 的分段为列 [4n, 4n+1, 4n+2, 4n+3]。
- “相同”：两个格子的布尔雷值相同（均为雷或均为空）。
- “不同”：两个格子的布尔雷值相反。

3) 计数对象、边界与越界处理
- 计数/比较对象是单个格子的布尔变量 (r, c)，r 为行，c 为列。
- 若某个分段的索引 4n..4n+3 中存在超出当前棋盘宽度的列（即 4n+3 >= width），则该分段整体忽略，不产生约束。
- 当行宽不足 4 时，该行不受本规则约束。

4) 规则语义（fill 阶段 与 create_constraints 阶段 等价性）
- 语义描述（自然语言）：对每一行、对每个有效的 4-长度分段 [a,b,c,d]（对应列 [4n,4n+1,4n+2,4n+3]）：
    - 若 b 与 c 相同，则要求 d 与 b 相同；
    - 否则（b 与 c 不同），要求 d 与 a 不同。
- create_constraints 应当以布尔相等/不等约束表达以上关系（等价关系与不等关系的布尔约束）。
- fill 阶段（生成解）必须保证最终输出的每一行在每个被考虑的分段上都满足上述约束。两阶段语义应一致：fill 的结果必须被 create_constraints 捕获，反之约束的可满足解在 fill 中是允许的。

5) 可验证样例（至少 2 个）
- 示例 1 (宽度 >=4)：行 = [M, M, M, ? , ...]（用 M 表示雷，· 表示空）
  - 对 4n=0 的分段: a=col0=M, b=col1=M, c=col2=M。此时 b==c 成立，故要求 d=col3 与 b 相同，即 col3 必须为 M。
- 示例 2 (宽度 >=4)：行 = [M, ·, M, ? , ...]
  - 对 4n=0 的分段: a=col0=M, b=col1=·, c=col2=M。此时 b!=c，故要求 d 与 a 不同，即 col3 必须为 ·（非雷）。
- 示例 3 (尾部不足 4 列)：宽度为 6 时，只对分段 n=0 ([0..3]) 生效，列 4..5 忽略，不产生约束。

验收要点：
- 在验收时，必须对若干行（包括边界行与中间行）抽查分段中的 a/b/c/d 格，核对 b==c 的分支与 b!=c 的分支实际约束结果是否一致。

作者: NT (2201963934)
最后编辑: 2026-05-16 04:23:46
"""

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard
from minesweepervariants.impl.summon.solver import Switch


class RuleMRG(AbstractMinesRule):
  """MRG (Merge) 左线规则：对每一行按 4 列为一组施加局部相等/不等约束。

  语义：对每一有效分段 [a,b,c,d]：若 b==c 则 d==b，否则 d!=a。
  """

  id = "MRG"
  name = "Merge"
  name.zh_CN = "合并"
  doc = "For each row, for every 4-length segment [a,b,c,d]: if b==c then d==b else d!=a."
  doc.zh_CN = "对每一行，逐个4格段 [a,b,c,d]：若 b==c 则 d==b，否则 d!=a。"
  tags = ["Local", "Row", "Lrule"]
  creation_time = "2026-05-16"
  author = ("NT", 2201963934)

  def __init__(self, board: "AbstractBoard" = None, data=None) -> None:
    super().__init__(board, data)

  def create_constraints(self, board: 'AbstractBoard', switch: 'Switch'):
    model = board.get_model()
    s = switch.get(model, self)

    # 快速返回：若棋盘无行或宽度为0则无需处理
    # 通过取任意交互键判断边界有效性
    keys = list(board.get_interactive_keys())
    if not keys:
      return

    for key in keys:
      pos_bound = board.boundary(key)
      # 按行处理
      for row_end in board.get_col_pos(pos_bound):
        col = board.get_row_pos(row_end)
        if not col or len(col) < 4:
          continue

        # 按 4 一段划分
        seg_count = len(col) // 4
        for n in range(seg_count):
          idx = 4 * n
          # 保证段完整
          if idx + 3 >= len(col):
            continue
          a_pos = col[idx]
          b_pos = col[idx + 1]
          c_pos = col[idx + 2]
          d_pos = col[idx + 3]

          a_var = board.get_variable(a_pos)
          b_var = board.get_variable(b_pos)
          c_var = board.get_variable(c_pos)
          d_var = board.get_variable(d_pos)

          # 使用更简单的等价形式：d 当且仅当 a, ~b, ~c 中最多一个为真
          # 等价为三个子句同时成立： (not a or b) && (not a or c) && (b or c)

          model.Add(a_var + 1 - b_var + 1 - c_var <= 1).OnlyEnforceIf([d_var, s])
          model.Add(a_var + 1 - b_var + 1 - c_var >= 2).OnlyEnforceIf([d_var.Not(), s])