"""
[SETU]涩图
"""

from minesweepervariants.abs import rule
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard
from ....config.config import IMAGE_CONFIG
import requests

class RuleSETU(AbstractMinesRule):
    name = ["SETU", "涩图"]
    doc = "不许涩涩!"

    def __init__(self, board: AbstractBoard, data=None):
        super().__init__(board, data)

        result = requests.get("https://api.lolicon.app/setu/v2", json={"size":"small"}).json()
        print(result)

        urls: dict = result["data"][0]["urls"]
        url = urls.get("small") or next(iter(urls.values()))

        IMAGE_CONFIG["background"]["image"] = url

    def create_constraints(self, board, switch):
        return
