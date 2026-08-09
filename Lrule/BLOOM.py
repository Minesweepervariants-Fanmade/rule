#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/08/09 17:44
# @Author  : NT (2201963934)
# @FileName: BLOOM.py
"""
[BLOOM] 泛光：无约束左线，生成的图片进行后处理，居中对齐缩放到适应1024x1024，
中心对齐padding黑色至2048x2048，使用卷积泛光处理，把泛光图缩放裁剪叠加回原图上
"""

from PIL import Image, ImageFilter, ImageChops

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.utils.image_create import register_final_image_postprocess_callback
from minesweepervariants.utils.tool import get_logger


class RuleBLOOM(AbstractMinesRule):
    """[BLOOM] 泛光效果后处理规则"""

    id = "BLOOM"
    name = "Bloom"
    name.zh_CN = "泛光"
    doc = "No constraint left-line rule, post-processes the generated image with bloom effect."
    doc.zh_CN = "无约束左线，生成的图片进行后处理，添加泛光效果。"
    author = ("NT", 2201963934)
    tags = ["Creative", "Fun", "WIP"]
    creation_time = "2026-08-09"

    def __init__(self, board=None, data=None) -> None:
        super().__init__(board, data)
        # 注册图片后处理回调，key 使用 "BLOOM" 保证唯一
        register_final_image_postprocess_callback(
            self._apply_bloom,
            key="BLOOM",
        )
        get_logger().info("[BLOOM] Bloom effect post-processing registered.")

    def _apply_bloom(self, image: Image.Image, board=None, config=None) -> Image.Image:
        """
        应用泛光效果的后处理回调。
        步骤：
        1. 缩放原图至适应1024x1024（保持比例，居中，黑色背景）。
        2. 将1024x1024图像中心对齐padding至2048x2048（黑色背景）。
        3. 对2048x2048图像进行高斯模糊（卷积泛光）。
        4. 从模糊图中裁剪出1024x1024中心区域。
        5. 将该区域缩放到原图尺寸。
        6. 将缩放后的泛光图以一定强度叠加回原图（使用屏幕混合或叠加）。
        """
        try:
            # 保留原图模式（支持RGBA）
            orig_mode = image.mode
            # 转换为RGB以便统一处理，如果有Alpha，我们处理RGB并还原Alpha
            has_alpha = orig_mode == 'RGBA'
            if has_alpha:
                alpha = image.split()[-1]
                rgb = image.convert('RGB')
            else:
                rgb = image.convert('RGB')

            orig_w, orig_h = rgb.size
            target_size = 1024
            big_size = 2048

            # 1. 缩放至适应1024x1024
            scale = min(target_size / orig_w, target_size / orig_h)
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)
            resized = rgb.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # 创建1024x1024黑底画布，居中放置
            canvas = Image.new('RGB', (target_size, target_size), (0, 0, 0))
            x_offset = (target_size - new_w) // 2
            y_offset = (target_size - new_h) // 2
            canvas.paste(resized, (x_offset, y_offset))

            # 2. 中心padding至2048x2048
            big_canvas = Image.new('RGB', (big_size, big_size), (0, 0, 0))
            pad = (big_size - target_size) // 2
            big_canvas.paste(canvas, (pad, pad))

            # 3. 高斯模糊（卷积泛光）
            # 半径可调，这里使用30，效果较柔和
            blurred = big_canvas.filter(ImageFilter.GaussianBlur(radius=30))

            # 4. 裁剪出1024x1024中心区域（即原来canvas的位置）
            crop_box = (pad, pad, pad + target_size, pad + target_size)
            glow_1024 = blurred.crop(crop_box)

            # 5. 缩放到原图尺寸
            glow_resized = glow_1024.resize((orig_w, orig_h), Image.Resampling.LANCZOS)

            # 6. 叠加回原图：使用屏幕混合（Screen）或加法混合
            # 此处使用 ImageChops.screen（屏幕混合），产生发光效果
            # 也可使用 add 混合，这里选择 screen 使亮部更亮
            result_rgb = ImageChops.screen(rgb, glow_resized)

            # 如果原图有Alpha，恢复Alpha通道
            if has_alpha:
                result_rgb.putalpha(alpha)

            get_logger().debug(f"[BLOOM] Applied bloom effect on {orig_w}x{orig_h} image.")
            return result_rgb

        except Exception as exc:
            get_logger().error(f"[BLOOM] Failed to apply bloom effect: {exc}")
            # 出错时返回原图
            return image

    def create_constraints(self, board, switch) -> None:
        """无约束，不添加任何CP-SAT约束"""
        return
