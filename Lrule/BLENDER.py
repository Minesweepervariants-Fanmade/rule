#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# @Time    : 2026/08/09
# @Author  : NT (2201963934)
# @FileName: BLENDER.py
"""
[BLENDER] 无约束左线，生成的图片进行后处理，使用 Blender 渲染图片。
需要安装 Blender 并确保 `blender` 命令在 PATH 中，或设置环境变量 BLENDER_EXECUTABLE。
"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional

from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.utils.image_create import register_final_image_postprocess_callback
from minesweepervariants.utils.impl_obj import get_seed
from minesweepervariants.utils.tool import get_logger


class RuleBLENDER(AbstractMinesRule):
    """[BLENDER] 无约束左线，图片后处理调用 Blender 渲染"""

    id = "BLENDER"
    name = "Blender Render"
    name.zh_CN = "Blender 渲染"
    doc = "No constraint left-line rule, post-processes the generated image using Blender."
    doc.zh_CN = "无约束左线，生成的图片进行后处理，使用 Blender 渲染图片。"
    author = ("NT", 2201963934)
    tags = ["Creative", "Fun", "WIP"]
    creation_time = "2026-08-09"

    def __init__(self, board=None, data=None) -> None:
        super().__init__(board, data)
        self.template_key = data
        # 检测 Blender 可执行文件
        self.blender_exec = self._find_blender()
        if self.blender_exec is None:
            get_logger().warning(
                "[BLENDER] 未找到 Blender 可执行文件，后处理将跳过。"
                "请安装 Blender 并确保 `blender` 命令在 PATH 中，"
                "或设置环境变量 BLENDER_EXECUTABLE。"
            )
            return
        # 检测渲染模板
        self.template_path = self._find_template()
        if self.template_path:
            get_logger().info(f"[BLENDER] 使用渲染模板: {self.template_path}（可在 Blender 中编辑该 .blend 修改场景）")
        else:
            get_logger().warning("[BLENDER] 未找到渲染模板，后处理将跳过并返回原图（可设置 BLENDER_TEMPLATE 指定模板）")
        # 注册图片后处理回调
        # 以模板为 key，使同一模板重复实例化时覆盖去重，不同模板可共存顺序执行
        register_final_image_postprocess_callback(
            self._apply_blender_render,
            key=f"BLENDER:{self.template_key}",
        )
        get_logger().info(f"[BLENDER] Blender 渲染后处理已注册，使用可执行文件: {self.blender_exec}")

    def _find_blender(self) -> Optional[str]:
        """查找 Blender 可执行文件路径。
        优先使用环境变量 BLENDER_EXECUTABLE，否则在 PATH 中查找 `blender` 命令。
        """
        env_path = os.environ.get("BLENDER_EXECUTABLE")
        if env_path and Path(env_path).exists():
            return env_path
        # 在 PATH 中查找
        blender_cmd = shutil.which("blender")
        if blender_cmd:
            return blender_cmd
        # 常见安装路径（Windows）
        common_paths = [
            r"C:\Program Files\Blender Foundation\Blender\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
        ]
        for p in common_paths:
            if Path(p).exists():
                return p
        return None

    def _find_template(self) -> Optional[str]:
        """查找可 GUI 编辑的 .blend 渲染模板。
        优先级：
        1. 环境变量 BLENDER_TEMPLATE（显式指定模板文件路径）
        2. 规则 data 参数（如 `BLENDER:monitor` 使用 assets/blender_template/monitor.blend）
        3. assets/blender_template/ 目录下第一个 .blend 文件（默认）
        模板要求：场景含一个材质，其节点树中有名为 `InputImage` 的图像纹理节点；
        渲染相机为场景活动相机；分辨率/引擎/灯光/背景随模板文件保存。
        """
        env_path = os.environ.get("BLENDER_TEMPLATE")
        if env_path and Path(env_path).exists():
            return str(Path(env_path))
        import minesweepervariants
        template_dir = Path(minesweepervariants.__file__).resolve().parent / "assets" / "blender_template"
        if not template_dir.is_dir():
            return None
        if self.template_key:
            candidate = template_dir / self.template_key
            if candidate.suffix.lower() != ".blend":
                candidate = candidate.with_suffix(".blend")
            if candidate.exists():
                return str(candidate)
            get_logger().warning(
                f"[BLENDER] 未找到模板 {candidate.name}（data={self.template_key}），回退到默认模板"
            )
        blends = sorted(template_dir.glob("*.blend"))
        if blends:
            return str(blends[0])
        return None

    def _apply_blender_render(self, image, board=None, config=None):
        """
        将 PIL Image 通过 Blender 渲染后返回新的 PIL Image。
        步骤：
        1. 将输入图像保存为临时 PNG 文件。
        2. 生成 Blender Python 脚本，该脚本导入图像作为纹理，渲染并输出。
        3. 调用 Blender 命令行执行脚本。
        4. 读取输出图像并返回。
        """
        if self.blender_exec is None or self.template_path is None:
            return image  # 无 Blender 或模板，直接返回原图

        # 确保输入图像为 RGB（忽略 alpha）
        if image.mode == "RGBA":
            rgb = image.convert("RGB")
        else:
            rgb = image.convert("RGB")

        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_in:
            input_path = tmp_in.name
            rgb.save(input_path, format="PNG")

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_out:
            output_path = tmp_out.name

        # 生成 Blender Python 脚本
        script_content = self._generate_template_script(input_path, output_path, self.template_path)

        # 脚本必须以 UTF-8 写入（Windows 下 tempfile 默认用 GBK，Blender 按 UTF-8 解析会失败）
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp_script:
            script_path = tmp_script.name
            tmp_script.write(script_content)

        try:
            # 调用 Blender
            cmd = [
                self.blender_exec,
                "--background",
                "--python", script_path,
                "--",
                input_path,
                output_path,
                self.template_path,
                str(get_seed()),
            ]
            get_logger().debug(f"[BLENDER] 执行命令: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,  # 超时 2 分钟
                check=False
            )
            if result.returncode != 0:
                get_logger().error(
                    f"[BLENDER] Blender 渲染失败 (返回码 {result.returncode}):\n"
                    f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
                )
                # 失败时返回原图
                return image
            # 读取渲染结果
            if Path(output_path).exists():
                from PIL import Image as PILImage
                rendered = PILImage.open(output_path).convert("RGBA")
                get_logger().debug(f"[BLENDER] 渲染成功，输出尺寸: {rendered.size}")
                return rendered
            else:
                get_logger().error(f"[BLENDER] 渲染输出文件不存在: {output_path}")
                return image
        except subprocess.TimeoutExpired:
            get_logger().error("[BLENDER] Blender 渲染超时")
            return image
        except Exception as exc:
            get_logger().error(f"[BLENDER] 渲染过程中发生异常: {exc}")
            return image
        finally:
            # 清理临时文件
            for p in (input_path, output_path, script_path):
                try:
                    if Path(p).exists():
                        Path(p).unlink()
                except OSError:
                    pass

    def _generate_template_script(self, input_path: str, output_path: str, template_path: str) -> str:
        """生成基于可编辑模板的 Blender 渲染脚本。
        打开模板 .blend，将名为 `InputImage` 的图像纹理节点换成输入图片后渲染。
        场景其余部分（相机/灯光/背景/分辨率/引擎）完全取自模板。
        """
        return f'''
import bpy
import sys

argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []
if len(argv) < 4:
    raise RuntimeError("需要输入图片路径、输出图片路径、模板路径和随机种子")
input_path = argv[0].replace("\\\\", "/")
output_path = argv[1].replace("\\\\", "/")
template_path = argv[2].replace("\\\\", "/")
random_seed = int(argv[3])

bpy.ops.wm.open_mainfile(filepath=template_path)

tex_node = None
for mat in bpy.data.materials:
    if mat.use_nodes and mat.node_tree:
        n = mat.node_tree.nodes.get("InputImage")
        if n is not None:
            tex_node = n
            break
if tex_node is None:
    raise RuntimeError("模板中未找到名为 InputImage 的图像纹理节点")

img = bpy.data.images.load(input_path, check_existing=False)
tex_node.image = img

scene = bpy.context.scene
scene["RandomSeed"] = random_seed
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = output_path
bpy.ops.render.render(write_still=True)
'''

    def create_constraints(self, board, switch) -> None:
        """无约束，不添加任何 CP-SAT 约束。"""
        return
