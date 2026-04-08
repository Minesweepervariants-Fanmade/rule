from ....abs.Lrule import AbstractMinesRule

from .connect import connect

class Rule3MA(AbstractMinesRule):
    name = ["3MA", "三雷区"]
    doc = "题板正好有三个四连通雷区"

    def create_constraints(self, board, switch):
        model = board.get_model()
        s = switch.get(model, self)

        connect(
            model=model,
            board=board,
            switch=s,
            component_num=3,
            nei_value=1
        )
    