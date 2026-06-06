from minesweepervariants.board import Board
from minesweepervariants.impl.summon.solver import Switch

from ....abs.Lrule import AbstractMinesRule

class RuleFS(AbstractMinesRule):
    id = "FS"
    name = "Fractal Subdivision"
    name.zh_CN = "分形"  # pyright: ignore[reportAttributeAccessIssue]
    doc = "The board is divided into n² equal square regions, each region is either all empty or all equal to an nxn pattern, where the pattern's mine positions correspond to non-empty regions and non-mine positions correspond to empty regions."
    doc.zh_CN = "题版边长为n²，全题版等分成n²个正方形区域，每个区域要么全空，要么全等于一个nxn的排布，该排布为雷的位置对应nxn的区域不是全空，为非雷的位置对应的区域全空。"  # pyright: ignore[reportAttributeAccessIssue]
    author = ("NT", 2201963934)
    tags = ["Creative", "Global", "Strict Shape", "Construction"]
    creation_time = "2026-05-27"

    def __init__(self, board=None, data=None):
        super().__init__(board, data)
        if board is None:
            return

        key = board.get_interactive_keys()[0]

        width = board.boundary(key).col + 1
        height = board.boundary(key).row + 1

        if width != height:
            raise ValueError(f"FS rule requires square board, but got width={width} and height={height}.")

        if int(width ** 0.5) ** 2 != width:
            raise ValueError(f"FS rule requires board size to be a perfect square, but got {width}.")

        self.n = int(width ** 0.5)


    def create_constraints(self, board: "Board", switch: "Switch"):
        model = board.get_model()
        s = switch.get(model, self)

        for key in board.get_interactive_keys():

            positions_vars = list(board(key=key, mode='variable', special='raw'))

            raw_map: dict[tuple[int, int], object] = {
                (pos.col, pos.row): raw_var
                for pos, raw_var in positions_vars
                if raw_var is not None
            }

            regions: dict[tuple[int, int], dict[tuple[int, int], object]] = {
                (i, j): {
                        (x, y): raw_map[(i * self.n + x, j * self.n + y)]
                        for x in range(self.n)
                        for y in range(self.n)
                }
                for i in range(self.n)
                for j in range(self.n)
            }

            region_vars = {
                (i, j): model.new_bool_var(f"region_{i}_{j}_is_pattern")
                for i in range(self.n)
                for j in range(self.n)
            }

            region_counters = {
                (i, j): model.new_int_var(0, self.n * self.n, f"region_{i}_{j}_mine_count")
                for i in range(self.n)
                for j in range(self.n)
            }
            for (i, j), region in regions.items():
                model.add(region_counters[(i, j)] == sum(region.values()))

                # If the region is a pattern, then all cells in the region must be mines or all must be empty
                for (x, y), cell in region.items():
                    model.add(cell == region_vars[(x, y)]).only_enforce_if(region_vars[(i, j)]).only_enforce_if(s)
                    model.add(cell == 0).only_enforce_if(region_vars[(i, j)].Not()).only_enforce_if(s)