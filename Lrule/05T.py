from minesweepervariants.position import Position

from ....abs.Lrule import AbstractMinesRule

def area(p1: Position, p2: Position, p3: Position):
    return abs(p1.x * (p2.y - p3.y) + p2.x * (p3.y - p1.y) + p3.x * (p1.y - p2.y)) / 2

class Rule05T(AbstractMinesRule):
    id = "0.5T"
    name = "0.5 Triangle"
    name.zh_CN = "0.5 三角形"
    doc = "Any three mines can not form a triangle with an area of 0.5"
    doc.zh_CN = "任意三个雷不能构成面积为 0.5 的三角形"
    tags = ["Variant", "Anti-Construction", "Global"]
    creation_time = "2026-06-04"
    author = ("无言之梦", 2452054817)

    def create_constraints(self, board, switch):
        model = board.get_model()
        s = switch.get(model, self)
        for k in board.get_interactive_keys():
            positions = [(p, v) for p, v in board(key=k, mode="variable")]
            n = len(positions)
            if n < 3:
                continue
            for i in range(n):
                for j in range(i+1, n):
                    for k in range(j+1, n):
                        pos1 = positions[i][0]
                        pos2 = positions[j][0]
                        pos3 = positions[k][0]
                        if area(pos1, pos2, pos3) == 0.5:
                            model.add(sum(board.batch([pos1, pos2, pos3], mode="variable")) != 3).only_enforce_if(s)

    def suggest_total(self, info: dict):
        ub = 0
        for key in info["interactive"]:
            total = info["total"][key]
            ub += total

        info["soft_fn"](ub * 0.295, 0)
