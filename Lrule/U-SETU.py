"""U-SETU: 直接使用参数图片作为最终图像。"""

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard
from minesweepervariants.utils.image_create import register_final_image_postprocess_callback
from minesweepervariants.utils.tool import get_logger
from .SETU import (
    parse_setu_image_data,
    resolve_setu_image,
    split_setu_parts,
    split_setu_key_value,
)


class RuleUSETU(AbstractMinesRule):
    id = "U-SETU"
    name = "Waifu Picture"
    name.zh_CN = "涩图"
    doc = "参数链接(支持URL/文件路径)"
    author = ("NT", 2201963934)

    def __init__(self, board: AbstractBoard, data=None):
        super().__init__(board, data)

        self.image_a_source = None
        self.image_a_keyword = None
        self.image_a = None

        self._parse_data(data)

        if self.image_a_source or self.image_a_keyword:
            self.image_a = resolve_setu_image(
                self.image_a_source,
                self.image_a_keyword,
                rule_name="U-SETU",
                default_random=False,
            )

        if self.image_a is not None:
            register_final_image_postprocess_callback(self._build_callback(), key="U-SETU")
        else:
            get_logger().warning("U-SETU 未提供图片链接，跳过最终图回调注册")

    def _parse_data(self, data):
        self.image_a_source, self.image_a_keyword = parse_setu_image_data(data)
        if not data:
            return
        parts = split_setu_parts(data)
        for part in parts[1:] if self.image_a_source else parts:
            key, val = split_setu_key_value(part)
            if key is None:
                continue
            key = key.strip().lower()
            val = val.strip().strip("\"'")
            try:
                if key == "white_pct":
                    self.white_pct = float(val)
                    self.auto_tune_top = False
                elif key == "black_pct":
                    self.black_pct = float(val)
                    self.auto_tune_black = False
                elif key == "invert_b":
                    self.invert_b = val.lower() in ("1", "true", "yes", "y", "on")
            except Exception as exc:
                get_logger().warning(f"U-SETU 参数解析失败[{part}]: {exc}")

    def _build_callback(self):
        def _callback(image_b, **_kwargs):
            try:
                if self.image_a is None:
                    return image_b
                get_logger().info("U-SETU 最终图回调已执行: 直接返回图片")
                return self.image_a.convert("RGBA")
            except Exception as exc:
                get_logger().error(f"U-SETU 最终图处理失败: {exc}")
                return image_b

        return _callback

    def create_constraints(self, board, switch):
        return
