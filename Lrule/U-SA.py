"""U-SA^ 反混合：对于一张透明图片，分别输入它在白底和黑底上混合颜色的结果，尝试还原原图。"""

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


class RuleUSA(AbstractMinesRule):
    id = "U-SA"
    name.zh_CN = "反混合"
    doc = "对于一张透明图片，分别输入它在白底和黑底上混合颜色的结果，尝试还原原图。"

    def __init__(self, board: AbstractBoard, data=None):
        super().__init__(board, data)

        self.image_a_source = None
        self.image_a_keyword = None
        self.image_a = None
        self.image_b_source = None
        self.image_b_keyword = None
        self.image_b = None
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
                rule_name="U-SA",
                default_random=False,
            )
        if self.image_b_source or self.image_b_keyword:
            self.image_b = resolve_setu_image(
                self.image_b_source,
                self.image_b_keyword,
                rule_name="U-SA",
                default_random=False,
            )

        if self.image_a is not None and self.image_b is not None:
            register_final_image_postprocess_callback(self._build_callback(), key="U-SAH")
        else:
            get_logger().warning("U-SA 未提供完整图片A/B链接，跳过背景融合回调注册")

    def _parse_data(self, data):
        if not data:
            return

        parts = split_setu_parts(data)
        if not parts:
            return

        unkeyed_images = []
        for part in parts:
            key, val = split_setu_key_value(part)
            if key is None:
                item = part.strip().strip("\"'")
                if item:
                    unkeyed_images.append(item)
                continue

            key = key.strip().lower()
            val = val.strip().strip("\"'")
            try:
                if key in ("a", "image_a", "a_url", "a_path", "source_a", "url_a", "path_a"):
                    if val:
                        self.image_a_source = val
                elif key in ("a_tag", "tag_a", "keyword_a", "k_a"):
                    if val:
                        self.image_a_keyword = val
                elif key in ("b", "image_b", "b_url", "b_path", "source_b", "url_b", "path_b"):
                    if val:
                        self.image_b_source = val
                elif key in ("b_tag", "tag_b", "keyword_b", "k_b"):
                    if val:
                        self.image_b_keyword = val
                elif key == "white_pct":
                    self.white_pct = float(val)
                    self.auto_tune_top = False
                elif key == "black_pct":
                    self.black_pct = float(val)
                    self.auto_tune_black = False
                elif key == "invert_b":
                    self.invert_b = val.lower() in ("1", "true", "yes", "y", "on")
            except Exception as exc:
                get_logger().warning(f"U-SA 参数解析失败[{part}]: {exc}")

        if self.image_a_source is None and self.image_a_keyword is None and unkeyed_images:
            self.image_a_source = unkeyed_images[0]
        if self.image_b_source is None and self.image_b_keyword is None and len(unkeyed_images) >= 2:
            self.image_b_source = unkeyed_images[1]

        if self.image_a_source is None and self.image_a_keyword is None:
            self.image_a_source, self.image_a_keyword = parse_setu_image_data(data)

    def _build_callback(self):
        def _callback(image_board, **_kwargs):
            try:
                if self.image_a is None or self.image_b is None:
                    return image_board
                merged = convert_images_to_rgba(
                    image_a=self.image_a,
                    image_b=self.image_b,
                    white_pct=self.white_pct,
                    black_pct=self.black_pct,
                    invert_b=self.invert_b,
                    auto_tune_top=self.auto_tune_top,
                    auto_tune_black=self.auto_tune_black,
                )
                get_logger().info("U-SA 最终图回调已执行: A(data)+B(data) 融合完成")
                return merged.convert("RGBA")
            except Exception as exc:
                get_logger().error(f"U-SA 背景融合失败: {exc}")
                return image_board

        return _callback

    def create_constraints(self, board, switch):
        return
