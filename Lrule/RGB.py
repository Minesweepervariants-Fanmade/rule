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
        生成随机网格多点渐变图。
        在图像上随机放置 6~12 个彩色控制点，每个像素的颜色由
        距离最近的 3 个控制点加权平均决定（基于反距离权重）。
        生成丰富的色彩过渡效果。
        """
        import math
        import random

        rng = random.Random()

        # 使用随机选择的三个颜色作为基础，生成 6~12 个控制点
        # 控制点颜色从这三个颜色中随机分配，并加入随机亮度微调
        base_colors = [self.color1, self.color2, self.color3]
        num_points = rng.randint(6, 12)
        rgb_colors = []
        for _ in range(num_points):
            base = rng.choice(base_colors)
            r, g, b = self._hex_to_rgb(base)
            # 加入随机微调 (±20)
            r = max(0, min(255, r + rng.randint(-20, 20)))
            g = max(0, min(255, g + rng.randint(-20, 20)))
            b = max(0, min(255, b + rng.randint(-20, 20)))
            rgb_colors.append((r, g, b))

        # 生成随机控制点位置 (x, y)
        margin = 0.1  # 避免点太靠近边缘
        points = []
        for _ in range(num_points):
            x = rng.uniform(margin * width, (1 - margin) * width)
            y = rng.uniform(margin * height, (1 - margin) * height)
            points.append((x, y))

        # 预计算每个点的权重缓存（加速）
        # 使用网格缓存：将图像分成小块，每块预计算最近的几个点
        # 为了代码简洁且保持良好性能，这里使用直接计算 + 优化：
        # 对于每个像素，只考虑最近的 3 个点
        img = Image.new("RGB", (width, height))
        pixels = img.load()

        # 可选：分块处理以提高性能
        # 对于大图，可以分块，但这里直接遍历所有像素
        for y in range(height):
            for x in range(width):
                # 计算到所有点的距离
                dists = []
                for idx, (px, py) in enumerate(points):
                    dx = x - px
                    dy = y - py
                    dist = math.hypot(dx, dy)
                    dists.append((dist, idx))

                # 按距离排序，取最近的 3 个
                dists.sort(key=lambda d: d[0])
                nearest = dists[:3]

                # 计算权重（反距离，加微小值防止除零）
                total_weight = 0.0
                weights = []
                for dist, idx in nearest:
                    if dist < 0.001:
                        # 正好在点上，直接使用该点颜色
                        r, g, b = rgb_colors[idx]
                        pixels[x, y] = (r, g, b)
                        break
                    w = 1.0 / (dist + 0.001)
                    weights.append((w, idx))
                    total_weight += w
                else:
                    # 加权平均
                    r = g = b = 0.0
                    for w, idx in weights:
                        cr, cg, cb = rgb_colors[idx]
                        r += cr * w / total_weight
                        g += cg * w / total_weight
                        b += cb * w / total_weight
                    pixels[x, y] = (int(r), int(g), int(b))

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
