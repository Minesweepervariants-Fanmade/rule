"""
[U-YY]一言：抛出一言（hitokoto.cn）。
"""

import json
from urllib import error, request

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard


class UYYError(Exception):
    """Base exception for U-YY."""


class UYYRequestError(UYYError):
    """Raised when hitokoto API request or decoding fails."""


class UYYHitokotoError(UYYError):
    """Raised with parsed hitokoto content."""

    def __init__(self, info: dict):
        self.info = info
        msg = (
            "U-YY 一言抛出 | "
            f"id={info['id']} | "
            f"uuid={info['uuid']} | "
            f"type={info['type']} | "
            f"from={info['from']} | "
            f"from_who={info['from_who']} | "
            f"creator={info['creator']} | "
            f"creator_uid={info['creator_uid']} | "
            f"length={info['length']} | "
            f"created_at={info['created_at']} | "
            f"hitokoto={info['hitokoto']}"
        )
        super().__init__(msg)


class RuleUYY(AbstractMinesRule):
    id = "U-YY"
    name = "Hitokoto"
    name.zh_CN = "一言"
    doc = "Fetches a random quote from hitokoto.cn"
    doc.zh_CN = "一言：抛出一言（hitokoto.cn）。"
    author = ("NT", 2201963934)
    tags = ["Creative", "Parameter"]

    def __init__(self, board: AbstractBoard, data=None):
        super().__init__(board, data)
        info = self._fetch_hitokoto(data)
        raise UYYHitokotoError(info)

    def _fetch_hitokoto(self, data=None):
        url = "https://v1.hitokoto.cn/"
        if isinstance(data, str) and data.strip():
            # Allow overriding endpoint for debugging or proxy usage.
            url = data.strip()

        try:
            req = request.Request(url=url, headers={"User-Agent": "MinesweeperVariants/U-YY"})
            with request.urlopen(req, timeout=8) as resp:
                body = resp.read().decode("utf-8")
        except (error.URLError, TimeoutError, ValueError):
            # Keep behavior usable in offline environments with API-compatible fallback payload.
            body = json.dumps(
                {
                    "id": -1,
                    "uuid": "offline-fallback",
                    "hitokoto": "网络不可达",
                    "type": "i",
                    "from": "v1.hitokoto.cn",
                    "from_who": None,
                    "creator": "U-YY",
                    "creator_uid": "0",
                    "length": 5,
                    "created_at": "0",
                },
                ensure_ascii=False,
            )

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise UYYRequestError(f"U-YY 解析 JSON 失败: {exc}") from exc

        if not isinstance(payload, dict):
            raise UYYRequestError("U-YY 返回格式错误: 顶层不是 JSON object")

        info = {
            "id": payload.get("id"),
            "uuid": payload.get("uuid"),
            "hitokoto": payload.get("hitokoto"),
            "type": payload.get("type"),
            "from": payload.get("from"),
            "from_who": payload.get("from_who"),
            "creator": payload.get("creator"),
            "creator_uid": payload.get("creator_uid"),
            "length": payload.get("length"),
            "created_at": payload.get("created_at"),
        }

        if info["hitokoto"] is None:
            raise UYYRequestError("U-YY 返回格式错误: 缺少 hitokoto 字段")

        return info

    def create_constraints(self, board: 'AbstractBoard', switch):
        return