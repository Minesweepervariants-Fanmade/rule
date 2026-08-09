#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
[RGB] RGB: 无约束左线, 生成的图片进行后处理, 使用正片叠底混合模式,
随机选择三个catppuccin mocha颜色生成三色渐变图, 叠加在原图上
"""

from PIL import Image, ImageChops, ImageDraw

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.board import Board
from minesweepervariants.utils.image_create import register_final_image_postprocess_callback
from minesweepervariants.utils.tool import get_logger, get_random

# Catppuccin Mocha 颜色 (来自 https://catppuccin.com/palette)
# 选择其中 14 种主要颜色进行随机抽取
CATPPUCCIN_MOCHA_COLORS = [
    "#f5e0dc",  # Rosewater
    "#f2cdcd",  # Flamingo
    "#f5c2e7",  # Pink
    "#cba6f7",  # Mauve
    "#f38ba8",  # Red
    "#eba0ac",  # Maroon
    "#fab387",  # Peach
    "#f9e2af",  # Yellow
    "#a6e3a1",  # Green
    "#94e2d5",  # Teal
    "#89dceb",  # Sky
    "#74c7ec",  # Sapphire
    "#89b4fa",  # Blue
    "#b4befe",  # Lavender
]


class RuleRGB(AbstractMinesRule):
    """[RGB] 规则：无约束左线，图片后处理叠加三色 Catppuccin Mocha 渐变"""

    id = "RGB"
    name = "RGB"
    name.zh_CN = "RGB"
    doc = (
        "No constraint left-line rule, post-processes the generated image with a "
        "three-color gradient overlay using multiply blending"
    )
    doc.zh_CN = (
        "无约束左线, 生成的图片进行后处理, 使用正片叠底混合模式, "
        "随机选择三个catppuccin mocha颜色生成三色渐变图, 叠加在原图上"
    )
    author = ("NT", 2201963934)
    tags = ["Creative", "Fun"]
    creation_time = "2026-08-09"

    def __init__(self, board: Board | None = None, data: str | None = None) -> None:
        super().__init__(board, data)

        # 随机选择三个 Catppuccin Mocha 颜色
        rng = get_random()
        chosen = rng.sample(CATPPUCCIN_MOCHA_COLORS, 3)
        self.color1, self.color2, self.color3 = chosen

        get_logger().info(
            f"[RGB] Selected Catppuccin Mocha colors: "
            f"{self.color1}, {self.color2}, {self.color3}"
        )

        # 注册图片后处理回调，key 使用 "RGB" 保证唯一
        register_final_image_postprocess_callback(
            self._apply_rgb_gradient,
            key="RGB",
        )

    def _hex_to_rgb(self, hex_color: str) -> tuple[int, int, int]:
        """将十六进制颜色字符串转换为 (R, G, B) 元组"""
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    def _create_gradient(
        self,
        width: int,
        height: int,
    ) -> Image.Image:
        """
        生成水平三色渐变图，从左到右依次从 color1 渐变到 color2 再到 color3。
        使用纯 PIL 逐列绘制，不依赖 numpy，适应各类环境。
        """
        r1, g1, b1 = self._hex_to_rgb(self.color1)
        r2, g2, b2 = self._hex_to_rgb(self.color2)
        r3, g3, b3 = self._hex_to_rgb(self.color3)

        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)

        for x in range(width):
            ratio = x / width  # 0.0 ~ 1.0
            if ratio < 0.5:
                # 前半段：color1 -> color2
                t = ratio * 2.0  # 0.0 ~ 1.0
                r = int(r1 + (r2 - r1) * t)
                g = int(g1 + (g2 - g1) * t)
                b = int(b1 + (b2 - b1) * t)
            else:
                # 后半段：color2 -> color3
                t = (ratio - 0.5) * 2.0  # 0.0 ~ 1.0
                r = int(r2 + (r3 - r2) * t)
                g = int(g2 + (g3 - g2) * t)
                b = int(b2 + (b3 - b2) * t)

            draw.line([(x, 0), (x, height)], fill=(r, g, b))

        return img

    def _apply_rgb_gradient(
        self,
        image: Image.Image,
        board: Board | None = None,
        config: dict | None = None,
    ) -> Image.Image:
        """
        图片后处理回调：将三色渐变图以正片叠底（Multiply）模式叠加在原图上。
        保留原图的 Alpha 通道，只对 RGB 通道执行正片叠底。
        """
        try:
            # 1. 分离 Alpha 通道（如果存在）
            if image.mode == "RGBA":
                alpha = image.split()[-1]
                rgb = image.convert("RGB")
            else:
                rgb = image.convert("RGB")
                alpha = None

            # 2. 生成三色渐变图（尺寸与 RGB 图像一致）
            gradient = self._create_gradient(rgb.width, rgb.height)

            # 3. 正片叠底混合（Multiply）
            #    result = (rgb * gradient) / 255
            multiplied = ImageChops.multiply(rgb, gradient)

            # 4. 恢复 Alpha 通道（如果有）
            if alpha is not None:
                multiplied.putalpha(alpha)

            get_logger().debug(
                f"[RGB] Applied gradient overlay: "
                f"{self.color1} -> {self.color2} -> {self.color3}, "
                f"size={multiplied.size}"
            )

            return multiplied

        except Exception as exc:
            get_logger().error(f"[RGB] Failed to apply gradient overlay: {exc}")
            # 回退返回原图，避免生成失败
            return image

    def create_constraints(self, board: Board, switch) -> None:
        """
        无约束左线规则：不向 CP-SAT 模型添加任何约束。
        仅通过 __init__ 中注册的图片后处理回调生效。
        """
        # 无约束，直接通过
        return
