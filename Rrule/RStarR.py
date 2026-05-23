"""
[R*R] 右线元规则：不直接创建任何线索格；在 fill 阶段根据当前题板的总雷数动态注入左线 R*。

规则拆分定义(验收基准):
1) 规则对象与适用范围:
  - 右线规则(Rrule)，作用对象是整张题板的生成/展示流程。
  - 本规则不生成任何线索格、不改写题面格值，只负责把“总雷数的奇偶性”翻译成一个左线规则 R*。
  - 派生出的左线规则必须是 R*:%2=0 或 R*:%2=1 之一，且只能选其一。

2) 核心术语精确定义:
  - 总雷数: 当前题板在生成阶段已经确定的全局雷数。
  - 奇偶性: 总雷数 mod 2 的结果；偶数对应 0，奇数对应 1。
  - 派生规则: 由本规则按奇偶性生成的左线规则 R*，其参数即 %2=0 或 %2=1。

3) 计数对象、边界条件、越界处理:
  - 计数对象不是局部邻域，而是全局总雷数。
  - 越界格、空洞格、非交互格都不参与“总雷数”本身的定义；它们只影响总雷数的求解结果。
  - 若总雷数尚未解析为非负整数，则必须显式失败，不能静默猜测奇偶性。

4) fill 阶段语义与 create_constraints 阶段语义的等价关系:
  - fill 阶段负责注入对应的左线 R* 子规则，不直接产生任何线索格。
  - create_constraints 阶段不再添加额外约束，保持空实现。
  - 语义上，本规则等价于“先判断总雷数奇偶，再添加对应的左线 R* 子规则”。

5) 可验证样例:
  - 5x5 题板若总雷数为 12，则本规则应派生 R*:%2=0。
  - 5x5 题板若总雷数为 13，则本规则应派生 R*:%2=1。
  - 同一盘面不应同时派生两个分支，也不应生成任何额外线索格。

验收要点:
  - 盘面上不应出现由本规则直接生成的线索格。
  - 规则集合中应能看到被注入的 R* 左线子规则。
  - 奇偶分支必须与总雷数一致，不能与局部格统计混用。

作者: NT
"""

from minesweepervariants.abs.Rrule import AbstractClueRule
from minesweepervariants.abs.board import AbstractBoard


class RuleRStarR(AbstractClueRule):
    id = "R*R"
    name = "R*R"
    name.zh_CN = "R*R"
    doc = "Inject R* as a left-line rule according to the parity of the total mine count"
    doc.zh_CN = "根据总雷数奇偶性注入左线 R*"
    tags = ["Meta", "Global", "Parameter", "Untagged"]
    creation_time = "2026-05-24"
    author = ("NT", 2201963934)

    def fill(self, board: "AbstractBoard") -> "AbstractBoard":
        total = sum(1 for _, value in board(target="F", mode="type") if value == "F")
        if not isinstance(total, int) or total < 0:
            raise ValueError("R*R 需要在总雷数已确定后才能派生 R*")

        data = f"={total}"
        board.get_rule_instance("R*", data=data, add=True)
        return board

    def create_constraints(self, board: "AbstractBoard", switch):
        return None
