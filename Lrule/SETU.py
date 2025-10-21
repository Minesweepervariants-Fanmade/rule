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

        servers = ["https://api.lolicon.app/setu/v2"]

        payload = {"r18": 0, "num": 1, "replace_url": "https://i.pixiv.cat"}

        if data:
            payload["tag"] = data.replace(","，"|").split(":")

        for server in servers:
            try:
                result = requests.post(server, json=payload).json()
                urls = result["data"][0]["urls"]
                url = urls.get("large") or next(iter(urls.values()))
            except:
                continue
            break
        else:
            raise ConnectionError("No server available")

        IMAGE_CONFIG["background"]["image"] = url
        IMAGE_CONFIG["white_base"] = True



    def create_constraints(self, board, switch):
        return
