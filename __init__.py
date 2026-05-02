#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# @Time    : 2025/06/03 04:23
# @Author  : Wu_RH
# @FileName: __init__.py

import os
import ast
import locale
from typing import Dict, Union


def _extract_author_text(node) -> tuple[str, str] | str | None:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (str, int)):
            return str(node.value).strip()
        return None
    if isinstance(node, (ast.List, ast.Tuple)):
        parts = []
        for elt in node.elts:
            text = _extract_author_text(elt)
            if text:
                parts.append(text)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0], parts[1]
        return None
    return None


def extract_module_docstring(filepath) -> Union[Dict, None]:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception:
        return None

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return None

    module_doc = ast.get_docstring(tree)

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        bases_info = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases_info.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases_info.append(base.attr)
            else:
                bases_info.append(str(base))

        x = 0
        if any("MinesClue" in b for b in bases_info):
            x |= 2
        elif any("Clue" in b for b in bases_info):
            x |= 4
        elif any("Mines" in b for b in bases_info):
            x |= 1

        info = {}
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    # 支持 name.<locale> = "..." 或 doc.<locale> = "..." 的写法
                    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                        base = target.value.id
                        attr = target.attr
                        if base in ("name", "doc"):
                            # 只处理常量字符串赋值
                            val = None
                            if isinstance(stmt.value, ast.Str):
                                val = stmt.value.s
                            elif isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                                val = stmt.value.value
                            if val and val.strip():
                                if base == "name":
                                    # 将已有 names 转为 dict 保存 i18n
                                    if "names" not in info:
                                        info["names"] = {}
                                    if isinstance(info.get("names"), list):
                                        # promote list to dict with default
                                        existing = info.get("names")
                                        info["names"] = {"default": existing[0]} if existing else {"default": ""}
                                    if not isinstance(info["names"], dict):
                                        info["names"] = {"default": str(info["names"])}
                                    info["names"][attr] = val.strip()
                                    info["x"] = x
                                    info["module_doc"] = module_doc
                                else:
                                    # doc
                                    if "doc" not in info:
                                        info["doc"] = {}
                                    if isinstance(info.get("doc"), str) and info.get("doc"):
                                        existing = info.get("doc")
                                        info["doc"] = {"default": existing}
                                    if not isinstance(info["doc"], dict):
                                        info["doc"] = {"default": str(info["doc"])}
                                    info["doc"][attr] = val.strip()
                                    info["x"] = x
                                    info["module_doc"] = module_doc
                        # continue processing other targets
                        continue

                for target in stmt.targets:
                    if (
                            isinstance(target, ast.Name) and target.id == "name" and
                            (
                                    isinstance(stmt.value, ast.Str)
                                    or isinstance(stmt.value, ast.List)
                                    or isinstance(stmt.value, ast.Tuple)
                                    or isinstance(stmt.value, ast.Dict)
                                    or isinstance(stmt.value, ast.Constant)
                            )
                    ):
                        # 支持多种写法：str / list/tuple / dict(i18n) / ast.Constant
                        # 列表或元组 -> names 列表
                        if isinstance(stmt.value, (ast.List, ast.Tuple)):
                            name_vals = []
                            for elt in stmt.value.elts:
                                val = None
                                if isinstance(elt, ast.Str):
                                    val = elt.s
                                elif isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    val = elt.value
                                if val and val.strip():
                                    name_vals.append(val.strip())
                            info["x"] = x
                            info["module_doc"] = module_doc
                            info["names"] = name_vals
                        # dict -> i18n mapping
                        elif isinstance(stmt.value, ast.Dict):
                            d = {}
                            for key_node, val_node in zip(stmt.value.keys, stmt.value.values):
                                if key_node is None:
                                    continue
                                if isinstance(key_node, ast.Str):
                                    k = key_node.s
                                elif isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                                    k = key_node.value
                                else:
                                    continue
                                if isinstance(val_node, ast.Str):
                                    v = val_node.s
                                elif isinstance(val_node, ast.Constant) and isinstance(val_node.value, str):
                                    v = val_node.value
                                else:
                                    continue
                                d[k] = v
                            if d:
                                info["x"] = x
                                info["module_doc"] = module_doc
                                info["names"] = d
                        # 单个字符串常量
                        elif isinstance(stmt.value, ast.Str) and stmt.value.s.strip():
                            name_val = stmt.value.s.strip()
                            info["x"] = x
                            info["module_doc"] = module_doc
                            info["names"] = [name_val]
                        elif isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value,
                                                                                 str) and stmt.value.value.strip():
                            name_val = stmt.value.value.strip()
                            info["x"] = x
                            info["module_doc"] = module_doc
                            info["names"] = [name_val]
                    if (
                            isinstance(target, ast.Name) and
                            target.id == "doc" and
                            (isinstance(stmt.value, ast.Str) or isinstance(stmt.value, ast.Dict) or isinstance(
                                stmt.value, ast.Constant))
                    ):
                        # 支持字符串或字典(i18n)形式
                        if isinstance(stmt.value, ast.Dict):
                            d = {}
                            for key_node, val_node in zip(stmt.value.keys, stmt.value.values):
                                if key_node is None:
                                    continue
                                if isinstance(key_node, ast.Str):
                                    k = key_node.s
                                elif isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                                    k = key_node.value
                                else:
                                    continue
                                if isinstance(val_node, ast.Str):
                                    v = val_node.s
                                elif isinstance(val_node, ast.Constant) and isinstance(val_node.value, str):
                                    v = val_node.value
                                else:
                                    continue
                                d[k] = v
                            if d:
                                info["doc"] = d
                        elif isinstance(stmt.value, ast.Str) and stmt.value.s.strip():
                            info["doc"] = stmt.value.s.strip()
                        elif isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value,
                                                                                 str) and stmt.value.value.strip():
                            info["doc"] = stmt.value.value.strip()
                    if (
                            isinstance(target, ast.Name) and
                            target.id == "author"
                    ):
                        author_val = _extract_author_text(stmt.value)
                        if author_val:
                            info["author"] = author_val
                    if (
                            isinstance(target, ast.Name) and
                            target.id == "id"
                    ):
                        # 规则id，期望为字符串常量
                        if isinstance(stmt.value, ast.Str) and stmt.value.s.strip():
                            info["id"] = stmt.value.s.strip()
                        elif isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value,
                                                                                 str) and stmt.value.value.strip():
                            info["id"] = stmt.value.value.strip()
        if "names" in info:
            return info
    return None


def scan_module_docstrings(directory):
    results = []
    for root, _, files in os.walk(directory):
        for name in files:
            if name.endswith('.py'):
                path = os.path.join(root, name)
                pck = extract_module_docstring(path)
                if pck is None:
                    continue
                m_doc = pck.get('module_doc', "")
                x = pck.get('x', 0)
                names = pck.get('names', [])
                doc = pck.get('doc', "")
                author = pck.get('author', ())
                rule_id = pck.get('id', "")
                results.append((m_doc, doc, x, names, author, rule_id))
    return results


def _text_from_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _iter_text_values(value):
    if isinstance(value, dict):
        for item in value.values():
            text = _text_from_value(item)
            if text:
                yield text
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            text = _text_from_value(item)
            if text:
                yield text
        return
    text = _text_from_value(value)
    if text:
        yield text


def _first_text(value) -> str:
    for text in _iter_text_values(value):
        return text
    return ""


def _normalize_i18n_map(value, fallback_text=""):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            text = _text_from_value(item)
            if text:
                result[str(key)] = text
        if result:
            return result
    elif isinstance(value, (list, tuple)):
        values = [_text_from_value(item) for item in value]
        values = [item for item in values if item]
        if values:
            return {"default": values[0]}
    else:
        text = _text_from_value(value)
        if text:
            return {"default": text}
    return {"default": fallback_text} if fallback_text else {}


def _normalize_author(author):
    author_name = ""
    author_id = ""
    if isinstance(author, (list, tuple)):
        if len(author) > 0:
            author_name = _text_from_value(author[0])
        if len(author) > 1:
            author_id = _text_from_value(author[1])
    elif isinstance(author, dict):
        author_name = _text_from_value(author.get("name", ""))
        author_id = _text_from_value(author.get("id", ""))
    else:
        author_name = _text_from_value(author)
    return {
        "name": author_name,
        "id": author_id,
    }


def _pick_image_name(rule_key, image_names):
    if not rule_key:
        return ""
    prefix = rule_key
    # 按照规范转义特殊字符
    prefix = prefix.replace("-", "--")
    prefix = prefix.replace("?", "-q")
    prefix = prefix.replace("*", "-a")
    prefix = prefix.replace("<", "-l")
    prefix = prefix.replace(">", "-g")
    prefix = prefix.replace("/", "-s")
    prefix = prefix.replace("\\", "-b")
    prefix = prefix.replace(":", "-c")
    for candidate in image_names:
        if candidate.startswith(prefix):
            return candidate
    return ""


def get_all_rules():
    results = {"L": [], "M": [], "R": []}
    dir_path = os.path.dirname(os.path.abspath(__file__))
    image_dir = os.path.join(dir_path, "image")
    image_names = []
    if os.path.isdir(image_dir):
        image_names = sorted(
            name for name in os.listdir(image_dir)
            if os.path.isfile(os.path.join(image_dir, name))
        )

    for m_doc, doc, x, names, author, rule_id in scan_module_docstrings(dir_path):
        if not names:
            continue

        rule_key = _first_text(rule_id) or _first_text(names)
        if not rule_key:
            continue

        rule_line = None
        if x == 1:
            rule_line = "L"
        elif x == 2:
            rule_line = "M"
        elif x == 4:
            rule_line = "R"
        if rule_line is None:
            continue

        name_map = _normalize_i18n_map(names, fallback_text=rule_key)
        doc_map = _normalize_i18n_map(doc)
        author_map = _normalize_author(author)
        image_name = _pick_image_name(rule_key, image_names)

        results[rule_line].append({
            "rule_line": rule_line,
            "id": _text_from_value(rule_id) or rule_key,
            "name": name_map,
            "doc": doc_map,
            "author": author_map,
            "image": image_name,
        })
    return results
