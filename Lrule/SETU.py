from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard
from ....config.config import IMAGE_CONFIG


def _looks_like_path(text: str) -> bool:
    lower = text.lower()
    if "\\" in text or "/" in text:
        return True
    return lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"))


def parse_setu_image_data(data) -> tuple[str | None, str | None]:
    image_source = None
    keyword = None

    if not data:
        return image_source, keyword

    parts = [x.strip() for x in str(data).split(";") if x.strip()]
    if not parts:
        return image_source, keyword

    if "=" not in parts[0]:
        image_source = parts[0]

    for part in parts[1:] if image_source else parts:
        if "=" not in part:
            continue
        key, val = part.split("=", 1)
        key = key.strip().lower()
        val = val.strip().strip("\"'")
        if not val:
            continue
        if key in ("a", "url", "path", "source"):
            image_source = val
        elif key in ("tag", "keyword", "k"):
            keyword = val
    return image_source, keyword


def _fetch_setu_url(keyword: str | None = None, rule_name: str = "SETU"):
    payload = {"r18": 0, "num": 1, "replace_url": "https://i.pixiv.cat"}
    if keyword:
        payload["tag"] = [x for x in keyword.replace(",", "|").split(":") if x]
    resp = requests.post("https://api.lolicon.app/setu/v2", json=payload, timeout=10)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    if not data:
        raise ValueError(f"{rule_name} 未获取到图片数据")
    urls = data[0].get("urls", {})
    if not urls:
        raise ValueError(f"{rule_name} 图片URL为空")
    return urls.get("large") or next(iter(urls.values()))


def _load_image_from_link(link: str, rule_name: str = "SETU"):
    link = link.strip().strip("\"'")
    if link.startswith(("http://", "https://")):
        resp = requests.get(link, timeout=10)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content)).convert("RGB")

    if link.startswith("file://"):
        link = link[7:]

    path = Path(link).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        raise FileNotFoundError(f"{rule_name} 图片路径不存在: {path}")
    return Image.open(path).convert("RGB")


def resolve_setu_image_ref(
    image_source: str | None,
    keyword: str | None,
    *,
    rule_name: str = "SETU",
    default_random: bool = True,
) -> str | None:
    if image_source:
        source = image_source.strip().strip("\"'")
        if source.startswith(("http://", "https://")):
            return source
        if source.startswith("file://"):
            source = source[7:]

        path = Path(source).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        if path.exists():
            return str(path)

        if _looks_like_path(source):
            raise FileNotFoundError(f"{rule_name} 图片路径不存在: {path}")

        return _fetch_setu_url(source, rule_name=rule_name)

    if keyword:
        return _fetch_setu_url(keyword, rule_name=rule_name)

    if default_random:
        return _fetch_setu_url(rule_name=rule_name)

    return None


def resolve_setu_image(
    image_source: str | None,
    keyword: str | None,
    *,
    rule_name: str = "SETU",
    default_random: bool = True,
):
    if image_source:
        source = image_source.strip().strip("\"'")
        if source.startswith(("http://", "https://", "file://")):
            return _load_image_from_link(source, rule_name=rule_name)

        path = Path(source).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        if path.exists():
            return Image.open(path).convert("RGB")

        if _looks_like_path(source):
            raise FileNotFoundError(f"{rule_name} 图片路径不存在: {path}")

        return _load_image_from_link(_fetch_setu_url(source, rule_name=rule_name), rule_name=rule_name)

    if keyword:
        return _load_image_from_link(_fetch_setu_url(keyword, rule_name=rule_name), rule_name=rule_name)

    if default_random:
        return _load_image_from_link(_fetch_setu_url(rule_name=rule_name), rule_name=rule_name)

    return None

class RuleSETU(AbstractMinesRule):
    name = ["SETU", "涩图"]
    doc = "禁止涩涩！"

    def __init__(self, board: AbstractBoard, data=None):
        super().__init__(board, data)

        self.image_source, self.keyword = parse_setu_image_data(data)
        IMAGE_CONFIG["background"]["image"] = resolve_setu_image_ref(
            self.image_source,
            self.keyword,
            rule_name="SETU",
            default_random=True,
        )
        IMAGE_CONFIG["white_base"] = True
    def create_constraints(self, board, switch):
        return
