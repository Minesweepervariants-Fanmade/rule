from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.utils.impl_obj import VALUE_CROSS, VALUE_CIRCLE
from minesweepervariants.impl.rule.Rrule.V import ValueV
from minesweepervariants.utils.tool import get_random

NAME_2I = "2I"

class Rule2I1C(AbstractMinesRule):
    name = ["2I1C", "残缺联通"]
    doc = "1.所有雷都必须根据副板指示的4对联通方向进行联通, 2.雷只有3种联通方法(上下/左右/对角/副对角)"

    def __init__(self, board = None, data=None):
        super().__init__(board, data)
        board.generate_board(NAME_2I, (3, 3))
        self.value = 6 if data is None else int(data)
        if self.value % 2 == 1:
            raise ValueError("2I1C的雷数必须为偶数")

    def init_board(self, board):
        random = get_random()
        pos = board.get_pos(1, 1, NAME_2I)
        obj = Value2I1C(pos, count=self.value)
        board[pos] = obj
        for p, _ in board("N", key=NAME_2I):
            board[p] = VALUE_CROSS

    def init_clear(self, board):
        for pos, obj in board(key=NAME_2I):
            if isinstance(obj, ValueV):
                continue
            board[pos] = None

    def create_constraints(self, board, switch):
        model = board.get_model()
        s1 = switch.get(model, self)
        s2 = switch.get(model, self)
        
        root_vars = {
            pos: model.NewBoolVar(f"{pos}:root")
            for pos, _ in board()
        }
        reach_vars = {
            pos: model.NewIntVar(0, len(root_vars) // 2, f"{pos}:root")
            for pos, _ in board()
        }

        # 每层只有一个root节点
        for key in board.get_interactive_keys():
            model.Add(sum(root_vars[pos] for pos, _ in board(key=key)) == 1)
        
        tag_pos = board.get_pos(1, 1, NAME_2I)
        model.Add(sum(board.get_variable(pos) for pos in tag_pos.neighbors(2)) == self.value).OnlyEnforceIf(s2)

        # tag_pos 上下/左右/两个对角的var相等约束
        neighbors = [
            ((-1, 0), (1, 0)),   # 上下
            ((0, -1), (0, 1)),   # 左右
            ((-1, -1), (1, 1)),  # 主对角线
            ((-1, 1), (1, -1)),  # 副对角线
        ]
        for (dx1, dy1), (dx2, dy2) in neighbors:
            p1 = tag_pos.shift(dx1, dy1)
            p2 = tag_pos.shift(dx2, dy2)
            if board.is_valid(p1) and board.is_valid(p2):
                v1 = board.get_variable(p1)
                v2 = board.get_variable(p2)
                model.Add(v1 == v2).OnlyEnforceIf(s2)
        model.Add(board.get_variable(tag_pos) == 0).OnlyEnforceIf(s2)

        for pos, var in board(mode="var"):
            # 如果为根节点 那么他reach为1
            model.Add(reach_vars[pos] == 1).OnlyEnforceIf(root_vars[pos])
            # 如果该格为非雷 则reach为0且不为root
            model.Add(reach_vars[pos] == 0).OnlyEnforceIf(var.Not())
            model.Add(reach_vars[pos] > 0).OnlyEnforceIf(var)
            model.Add(root_vars[pos] == 0).OnlyEnforceIf(var.Not())

            # 遍历周围八格
            tmp_list = []
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    tmp = model.NewBoolVar(f"{pos}:tmp:{dx},{dy}")
                    n_pos = pos.shift(dx, dy)
                    if not board.is_valid(n_pos):
                        continue
                    t_pos = tag_pos.shift(dx, dy)
                    n_var = board.get_variable(n_pos)
                    t_var = board.get_variable(t_pos)
                    # 如果该格为雷且不是root 那么他的reach等于某个邻居的reach+1
                    model.Add(
                        reach_vars[pos] == reach_vars[n_pos] + 1
                    ).OnlyEnforceIf([
                        var, root_vars[pos].Not(), n_var, t_var, tmp
                    ])
                    model.Add(tmp == 0).OnlyEnforceIf(var.Not())
                    model.Add(tmp == 0).OnlyEnforceIf(root_vars[pos])
                    model.Add(tmp == 0).OnlyEnforceIf(n_var.Not())
                    model.Add(tmp == 0).OnlyEnforceIf(t_var.Not())
                    tmp_list.append(tmp)

            model.Add(sum(tmp_list) == 1).OnlyEnforceIf([var, root_vars[pos].Not(), s1])


class Value2I1C(ValueV):
    def create_constraints(self, board, switch):
        pass

    @classmethod
    def type(cls) -> bytes:
        return Rule2I1C.name[0].encode()
