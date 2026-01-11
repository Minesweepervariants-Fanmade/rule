"""
[THEME]设置题板主题
"""

from minesweepervariants.abs import rule
from minesweepervariants.abs.Lrule import AbstractMinesRule
from minesweepervariants.abs.board import AbstractBoard
from ....config.config import IMAGE_CONFIG
import requests

THEME = {
    "default": {
        # 背景色设置
        "background": {
            "white": "#FFFFFF",
            "black": "#000000",
            "image": ""
        },

        # 网格线设置
        "grid_line": {
            "white_bg": "#000000",
            "black_bg": "#FFFFFF",
            "width": 0.032
        },

        # 文本设置
        "text": {
            "black": "#FFFFFF",
            "white": "#000000",
            "anchor": "mm"
        },

        # 染色区域
        "dye": {
            "white_bg": "#B3B3B3",
            "black_bg": "#4C4C4C"
        },

        # 描边颜色
        "stroke": {
            "white_bg": "#808080",
            "black_bg": "#D3D3D3"
        },

        # 位置标签（例如 X=E）
        "pos_label": {
            # 标签X=E设置
            "white_bg": "#808080",
            "black_bg": "#808080",
            "size": 0.25
        },

        "assets": "assets",

        # 字体设置
        "font": {
            "name": "CopperplateCC-Heavy.ttf"
        },

        # 边距设置
        "margin": {
            "top_left_right_ratio": 0.7,
            "bottom_ratio": 0.7
        },

        # 坐标轴标签字体比例
        "axis_label": {
            "font_ratio": 0.5
        },

        # 角标尺寸
        "corner": {
            "mini_font_ratio": 0.23
        }
    },
    "print": {
        # 背景色设置
        "background": {
            "white": "#FFFFFF",
            "black": "#000000",
            "image": ""
        },

        # 网格线设置
        "grid_line": {
            "white_bg": "#000000",
            "black_bg": "#FFFFFF",
            "width": 0.032
        },

        # 文本设置
        "text": {
            "black": "#FFFFFF",
            "white": "#000000",
            "anchor": "mm"
        },

        # 染色区域
        "dye": {
            "white_bg": "#B3B3B3",
            "black_bg": "#4C4C4C"
        },

        # 描边颜色
        "stroke": {
            "white_bg": "#808080",
            "black_bg": "#D3D3D3"
        },

        # 位置标签（例如 X=E）
        "pos_label": {
            # 标签X=E设置
            "white_bg": "#808080",
            "black_bg": "#808080",
            "size": 0.25
        },

        "assets": "assets/white",

        # 字体设置
        "font": {
            "name": "CopperplateCC-Heavy.ttf"
        },

        # 边距设置
        "margin": {
            "top_left_right_ratio": 0.7,
            "bottom_ratio": 0.7
        },

        # 坐标轴标签字体比例
        "axis_label": {
            "font_ratio": 0.5
        },

        # 角标尺寸
        "corner": {
            "mini_font_ratio": 0.23
        },

        "white_base": True,

        "experiment_svg": False
    }
}

def update_dict(d: dict, u: dict):
    for k, v in u.items():
        if isinstance(v, dict):
            d[k] = update_dict(d.get(k, {}), v)
        else:
            d[k] = v
    return d

class RuleSETU(AbstractMinesRule):
    name = ["THEME", "主题"]
    doc = "设置题板主题"

    def __init__(self, board: AbstractBoard, data=None):
        super().__init__(board, data)
        data = data or "default"
        if data not in THEME:
            raise ValueError(f"未知主题 {data}")

        update_dict(IMAGE_CONFIG, THEME[data])

    def create_constraints(self, board, switch):
        return
