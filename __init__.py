#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# @Time    : 2025/06/03 04:23
# @Author  : Wu_RH
# @FileName: __init__.py

import os
import ast
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
                        elif isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str) and stmt.value.value.strip():
                            name_val = stmt.value.value.strip()
                            info["x"] = x
                            info["module_doc"] = module_doc
                            info["names"] = [name_val]
                    if (
                        isinstance(target, ast.Name) and
                        target.id == "doc" and
                        (isinstance(stmt.value, ast.Str) or isinstance(stmt.value, ast.Dict) or isinstance(stmt.value, ast.Constant))
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
                        elif isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str) and stmt.value.value.strip():
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
                        elif isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str) and stmt.value.value.strip():
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


def get_all_rules():
    results = {"R": {}, "M": {}, "L": {}, "O": {}}
    dir_path = os.path.dirname(os.path.abspath(__file__))
    for m_doc, doc, x, names, author, rule_id in scan_module_docstrings(dir_path):
        if not names:
            continue
        # determine the rule key: prefer explicit id, otherwise fall back to first name
        if rule_id:
            key_name = rule_id
            remaining = names
        else:
            if isinstance(names, dict):
                # if names is i18n dict, take an arbitrary first value as display name
                items = list(names.items())
                if items:
                    key_name = items[0][1]
                    remaining = [v for _, v in items[1:]]
                else:
                    continue
            elif isinstance(names, list):
                key_name = names[0]
                remaining = names[1:]
            else:
                key_name = str(names)
                remaining = []
        rule_line = None
        if x == 1:
            rule_line = "L"
        elif x == 2:
            rule_line = "M"
        elif x == 4:
            rule_line = "R"
        if rule_line is None:
            continue
        # Normalize output: always include full i18n dicts if present
        entry_names = []
        names_i18n = {}
        if isinstance(names, dict):
            names_i18n = names
            # derive a fallback list of display names from dict values
            entry_names = [v for _, v in names.items()]
        elif isinstance(names, list):
            entry_names = names
        else:
            entry_names = [str(names)]

        entry_doc = doc if isinstance(doc, str) else (next(iter(doc.values())) if isinstance(doc, dict) and doc else "")
        doc_i18n = doc if isinstance(doc, dict) else {}

        results[rule_line][key_name] = {
            "names": entry_names,
            "names_i18n": names_i18n,
            "doc": entry_doc,
            "doc_i18n": doc_i18n,
            "module_doc": m_doc,
            "author": author,
            "id": rule_id,
        }
    return results
