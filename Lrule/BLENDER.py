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
        # 检测 Blender 可执行文件
        self.blender_exec = self._find_blender()
        if self.blender_exec is None:
            get_logger().warning(
                "[BLENDER] 未找到 Blender 可执行文件，后处理将跳过。"
                "请安装 Blender 并确保 `blender` 命令在 PATH 中，"
                "或设置环境变量 BLENDER_EXECUTABLE。"
            )
            return
        # 注册图片后处理回调
        register_final_image_postprocess_callback(
            self._apply_blender_render,
            key="BLENDER",
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

    def _apply_blender_render(self, image, board=None, config=None):
        """
        将 PIL Image 通过 Blender 渲染后返回新的 PIL Image。
        步骤：
        1. 将输入图像保存为临时 PNG 文件。
        2. 生成 Blender Python 脚本，该脚本导入图像作为纹理，渲染并输出。
        3. 调用 Blender 命令行执行脚本。
        4. 读取输出图像并返回。
        """
        if self.blender_exec is None:
            return image  # 无 Blender，直接返回原图

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
        script_content = self._generate_blender_script(input_path, output_path)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp_script:
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
                output_path
            ]
            get_logger().debug(f"[BLENDER] 执行命令: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
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

    def _generate_blender_script(self, input_path: str, output_path: str) -> str:
        """生成用于 Blender 渲染的 Python 脚本。"""
        return f'''
import bpy
import sys

# 接收命令行参数（在 -- 之后）
argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []
if len(argv) < 2:
    raise RuntimeError("需要输入图片路径和输出图片路径")
input_path = argv[0]
output_path = argv[1]

# 清空场景
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# 创建平面
bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
plane = bpy.context.object

# 创建材质并加载图像纹理
mat = bpy.data.materials.new(name="ImageMaterial")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
# 清除默认节点
nodes.clear()
# 图像纹理节点
tex_image = nodes.new(type='ShaderNodeTexImage')
try:
    tex_image.image = bpy.data.images.load(input_path)
except Exception as e:
    raise RuntimeError(f"加载图像失败: {{e}}")
# 原理化 BSDF
bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
# 输出
output = nodes.new(type='ShaderNodeOutputMaterial')
# 连接
links.new(tex_image.outputs['Color'], bsdf.inputs['Base Color'])
links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
plane.data.materials.append(mat)

# 设置相机（俯视）
bpy.ops.object.camera_add(location=(0, 0, 2))
camera = bpy.context.object
camera.rotation_euler = (0, 0, 0)

# 设置渲染引擎和输出格式
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'  # 快速渲染
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = output_path

# 渲染
bpy.ops.render.render(write_still=True)
'''

    def create_constraints(self, board, switch) -> None:
        """无约束，不添加任何 CP-SAT 约束。"""
        return
