"""SETU^: 将参数图片作为A图并与SETU背景图融合。"""

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard
from minesweepervariants.utils.convert_images_to_rgba import convert_images_to_rgba
from minesweepervariants.utils.image_create import register_final_image_postprocess_callback
from minesweepervariants.utils.tool import get_logger
from .SETU import (
    parse_setu_image_data,
    resolve_setu_image,
    split_setu_parts,
    split_setu_key_value,
)


class RuleSETUHat(AbstractMinesRule):
    id = "SETU^"
    name = "SETUH"
    name.zh_CN = "涩图融合"
    doc = "Parameter image URL (supporting URL/file path) as image A, merged with generated board image B and replacing final board image"
    doc.zh_CN = "参数链接(支持URL/文件路径)作为A图，与已生成题板图B融合并替换最终题板图"
    author = ("NT", 2201963934)

    def __init__(self, board: AbstractBoard, data=None):
        super().__init__(board, data)

        self.image_a_source = None
        self.image_a_keyword = None
        self.image_a = None
        self.white_pct = 20.0
        self.black_pct = 0.0
        self.invert_b = False
        self.auto_tune_top = True
        self.auto_tune_black = True

        self._parse_data(data)

        if self.image_a_source or self.image_a_keyword:
            self.image_a = resolve_setu_image(
                self.image_a_source,
                self.image_a_keyword,
                rule_name="SETU^",
                default_random=False,
            )

        if self.image_a is not None:
            register_final_image_postprocess_callback(self._build_callback(), key="SETUH")
        else:
            get_logger().warning("SETU^ 未提供图片A链接，跳过背景融合回调注册")

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
                get_logger().warning(f"SETU^ 参数解析失败[{part}]: {exc}")

    def _build_callback(self):
        def _callback(image_b, **_kwargs):
            try:
                if self.image_a is None:
                    return image_b
                merged = convert_images_to_rgba(
                    image_a=self.image_a,
                    image_b=image_b.convert("RGB"),
                    white_pct=self.white_pct,
                    black_pct=self.black_pct,
                    invert_b=self.invert_b,
                    auto_tune_top=self.auto_tune_top,
                    auto_tune_black=self.auto_tune_black,
                )
                get_logger().info("SETU^ 最终图回调已执行: A(url)+B(board) 融合完成")
                return merged.convert("RGBA")
            except Exception as exc:
                get_logger().error(f"SETU^ 背景融合失败: {exc}")
                return image_b

        return _callback

    def create_constraints(self, board, switch):
        return
