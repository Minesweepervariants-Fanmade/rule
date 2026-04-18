"""
[U-LLM]随机规则点子：从纸笔谜题名词库中抽取词语，交由 LLM 生成规则描述并抛出。

规则拆分定义（监工验收基线）
1) 规则对象与适用范围
- 规则类型: Lrule（全局约束类型），不对单格线索进行赋值，不参与 fill 阶段。
- 作用对象: 全局文本输出事件（抛出规则描述），不改变棋盘雷/数状态。
- 执行时机: 规则初始化阶段（__init__）完成参数解析与远程调用，随后通过异常抛出结果。

2) 核心术语定义
- 纸笔谜题名词库: 一组可被随机采样的术语字符串集合；若未外部提供则使用内置默认词库。
- 抽取词数量(noun_count): 从名词库中无放回抽取的词数，默认 3，且需限定最小值 1。
- 额外提示词(extra_prompt): 追加到系统/用户提示中的自由文本，可为空。
- 自定义替换词(replace_terms): 若提供则优先作为联想输入词，覆盖随机抽取结果。
- OpenAI 兼容模式: 通过环境变量提供 endpoint/model/api_key 等配置，按 Chat Completions 兼容接口请求。

3) 计数对象、边界条件、越界处理
- 计数对象仅为“联想输入词条数”。
- noun_count > 词库大小时，按词库大小截断；noun_count <= 0 时回退为 1。
- replace_terms 解析后若为空，回退到随机抽取流程。
- 环境变量缺失、HTTP 错误、JSON 结构错误、响应缺失文本时，均需抛出可读错误并包含关键上下文。

4) fill 语义与 create_constraints 语义等价关系
- 本规则为 Lrule，全程不定义 fill；create_constraints 仅空实现（不添加任何模型约束）。
- 语义等价性: “无 fill + 无约束添加” 与 “该规则仅输出文本、不影响求解空间”完全等价。

5) 可验证样例
- 样例A（默认）: data 为空，noun_count=3，随机抽取 3 词并成功调用 LLM，抛出“仅一句规则描述”的异常文本。
- 样例B（替换词）: data 指定 replace_terms=镜像,连通,奇偶；即使 noun_count=5 也应优先使用这 3 词输入 LLM。
- 样例C（边界）: noun_count=0 时按 1 处理；noun_count 超过词库时截断到词库大小。
"""

import json
import os
import random

try:
    from openai import OpenAI
    from openai import APIError as OpenAIAPIError
    from openai import APIConnectionError as OpenAIConnectionError
    from openai import AuthenticationError as OpenAIAuthenticationError
    from openai import RateLimitError as OpenAIRateLimitError
    from openai import Timeout as OpenAITimeout
except ImportError:
    pass

from ....abs.Lrule import AbstractMinesRule
from ....abs.board import AbstractBoard
from ....utils.tool import get_logger


class ULLMError(Exception):
    """Base exception for U-LLM."""


class ULLMConfigError(ULLMError):
    """Raised when environment or input configuration is invalid."""


class ULLMRequestError(ULLMError):
    """Raised when OpenAI-compatible request/response fails."""


class ULLMGeneratedRuleError(ULLMError):
    """Raised with the generated rule text for CLI display."""

    def __init__(self, description):
        super().__init__(description)


def _env_first(*keys):
    for key in keys:
        value = os.getenv(key)
        if value is not None and value.strip():
            return value.strip()
    return None


class RuleULLM(AbstractMinesRule):
    name = ["U-LLM", "随机规则点子"]
    doc = "随机规则点子：随机抽词并由 LLM 联想生成规则描述后抛出。"
    author = ("NT", 2201963934)

    _DEFAULT_NOUNS = \
    "雷格 非雷格 " \
    "镜像 连通 奇偶 " \
    "路径 颜色 数字 " \
    "线索值 雷值 " \
    "箭头 数字 " \
    "周围四格 周围八格 " \
    "矩形 非矩形 " \
    "等于 大于 小于 " \
    "至少一个 最多一个 恰好一个 " \
    "任意 全部 没有 " \
    "相同 不同 " \
    "边界 内部 外部 " \
    "相邻 不相邻 " \
    "同区 不同区 " \
    "对称 不对称 " \
    "解除 不接触 " \
    "染色格 非染色格" \
    "方向 距离" \
    "".strip().split()

    def __init__(self, board: AbstractBoard, data=None):
        super().__init__(board, data)
        options = self._parse_data(data)
        noun_count = self._normalize_noun_count(options.get("noun_count", 3))
        extra_prompt = str(options.get("extra_prompt", "")).strip()
        terms = self._resolve_terms(options.get("replace_terms"), noun_count)
        description = self._generate_description(terms, extra_prompt)
        raise ULLMGeneratedRuleError(description=description)

    def _parse_data(self, data):
        if data is None:
            return {}

        if isinstance(data, dict):
            return dict(data)

        if isinstance(data, str):
            text = data.strip()
            if not text:
                return {}
            if "=" not in text:
                return {"extra_prompt": text}

            parsed = {}
            for seg in text.split(";"):
                part = seg.strip()
                if not part:
                    continue
                if "=" not in part:
                    key = part.strip()
                    if key:
                        parsed[key] = ""
                    continue
                key, value = part.split("=", 1)
                key = key.strip()
                if not key:
                    continue
                parsed[key] = value.strip()
            return parsed

        raise ULLMConfigError(f"U-LLM 不支持的 data 类型: {type(data).__name__}")

    def _normalize_noun_count(self, value):
        try:
            num = int(value)
        except (TypeError, ValueError):
            raise ULLMConfigError(f"U-LLM noun_count 不是有效整数: {value}")

        if num <= 0:
            num = 1
        if num > len(self._DEFAULT_NOUNS):
            num = len(self._DEFAULT_NOUNS)
        return num

    def _resolve_terms(self, replace_terms_raw, noun_count):
        if replace_terms_raw is not None:
            if isinstance(replace_terms_raw, (list, tuple)):
                terms = [str(x).strip() for x in replace_terms_raw if str(x).strip()]
            else:
                terms = [x.strip() for x in str(replace_terms_raw).split(",") if x.strip()]
            if terms:
                return terms

        return random.sample(self._DEFAULT_NOUNS, noun_count)

    def _generate_description(self, terms, extra_prompt):
        endpoint = _env_first("OPENAI_ENDPOINT", "OPENAI_BASE_URL", "OPENAI_API_BASE")
        api_key = _env_first("OPENAI_API_KEY")
        model = _env_first("OPENAI_MODEL")

        missing = []
        if endpoint is None:
            missing.append("OPENAI_ENDPOINT/OPENAI_BASE_URL/OPENAI_API_BASE")
        if api_key is None:
            missing.append("OPENAI_API_KEY")
        if model is None:
            missing.append("OPENAI_MODEL")
        if missing:
            raise ULLMConfigError(f"U-LLM 环境变量缺失: {', '.join(missing)}")

        assert endpoint is not None and api_key is not None and model is not None

        base_url = endpoint.strip()
        joined_terms = "、".join(terms)
        user_prompt = (
            f"请围绕这些名词构造扫雷变体规则: {joined_terms}。"
        )
        if extra_prompt:
            user_prompt += f" 额外提示: {extra_prompt}。"

        client = OpenAI(api_key=api_key, base_url=base_url)
        get_logger().info(f"[U-LLM] selected terms: {joined_terms}")
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是扫雷变体规则设计助手。你擅长设计纸笔谜题风格的扫雷规则文本。" \
                                   "请基于用户给出的名词联想并生成一段简洁、可读、可执行、有创意的规则描述。" \
                                   "先在内部充分思考，再仅输出一句规则描述；不要暴露任何思考过程。" \
                                   "描述应聚焦扫雷变体玩法，不要输出代码，不要分点。\n" \
                                   "最终输出格式必须是且只能是`[规则代号(一般是两三个大写字母或数字)]规则中文名称(规则英文名称): 一句中文规则描述`。" \
                                   "不分点、不解释、不加前后缀标签、但要说明是左右线规则中的哪种。\n\n" \
                                   "#项目说明: \n" \
                                   "- 左线规则表示不针对某个具体格子, 而是整个盘面均生效的, 例如:'所有雷格构成一条蛇', '所有行列的雷数相同'等。\n" \
                                   "- 右线规则表示针对每个格子(称为线索格), 线索表示该线索格附近区域的某种关系, 例如:'线索数表示周围八格雷数', '线索数表示到最近两个雷的距离乘积'等。\n" \
                                   "- 小部分规则可能与染色情况有关. 染色分为黑白两色. \n\n" \
                                   "##示例: `[2A]面积(Area): 右线规则。线索表示四方向相邻雷区域的面积之和。`"
                                   },
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.9,
            )
        except OpenAIAuthenticationError as exc:
            raise ULLMRequestError(f"U-LLM 认证失败，请检查 OPENAI_API_KEY: {exc}") from exc
        except OpenAIRateLimitError as exc:
            raise ULLMRequestError(f"U-LLM 调用被限流: {exc}") from exc
        except OpenAIConnectionError as exc:
            raise ULLMRequestError(f"U-LLM 网络连接失败(base_url={base_url}): {exc}") from exc
        except OpenAIAPIError as exc:
            raise ULLMRequestError(f"U-LLM 接口调用失败(model={model}, base_url={base_url}): {exc}") from exc
        except Exception as exc:
            raise ULLMRequestError(f"U-LLM 未知调用异常(model={model}, base_url={base_url}): {exc}") from exc

        try:
            description = response.choices[0].message.content
            description = description.strip() if description is not None else ""
        except (AttributeError, IndexError, TypeError) as exc:
            raw = json.dumps(response.model_dump(), ensure_ascii=False)
            raise ULLMRequestError(f"U-LLM 响应缺少文本内容: {raw}") from exc

        if not description:
            raw = json.dumps(response.model_dump(), ensure_ascii=False)
            raise ULLMRequestError(f"U-LLM 响应文本为空: {raw}")

        return description

    def create_constraints(self, board: 'AbstractBoard', switch):
        return
