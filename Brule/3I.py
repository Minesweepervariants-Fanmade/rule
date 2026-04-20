"""
[3I]反相(Inverted): 染色格中非雷视为雷，雷视为非雷
"""
from minesweepervariants.abs.Brule import AbstractProxyBoard, AbstractBoardRule

class Rule3I(AbstractBoardRule):
    @classmethod
    def get_board(cls):
        return Board3I

class Board3I(AbstractProxyBoard):
    def get_type(self, pos):
        t = super().get_type(pos)
        d = self.get_dyed(pos)
        if not d:
            return t
        if t == "F":
            return "C"
        elif t == "C":
            return "F"
        else:
            return t
    
    def get_variable(self, pos):
        d = self.get_dyed(pos)
        if not d:
            return super().get_variable(pos)
        return super().get_variable(pos).Not()
        
