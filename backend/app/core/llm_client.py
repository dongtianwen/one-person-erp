"""v2.0 AI Agent 闭环——LLM Provider 抽象层。

三档 Provider：none（规则-only）/ local（Ollama）/ api（外部 OpenAI 兼容）。
"""

import json
import os
import re
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx

from app.core.constants import (
    LLM_PROVIDER_NONE,
    LLM_PROVIDER_LOCAL,
    LLM_PROVIDER_API,
    LLM_RETRY_MAX_ATTEMPTS,
    LLM_TIMEOUT_SECONDS,
    FEEDBACK_CONTEXT_MAX_RECORDS,
    SUGGESTION_TYPE_WHITELIST,
    PRIORITY_WHITELIST,
    FEEDBACK_WEIGHT_RULES,
)
from app.core.error_codes import ERROR_CODES

logger = logging.getLogger(__name__)

# ── Prompt 模板 ──────────────────────────────────────────────────

ENHANCE_SYSTEM_PROMPT = (
    "你是一个资深经营顾问，请将以下业务异常数据改写为面向管理者的详实专业建议。"
    "要求："
    "1. 输出纯 JSON 数组，每项必须包含 index（与输入的 index 数值保持一致）、title（≤20字的简洁标题）和 description（必须3-5句话，每句都要有实质内容）。"
    "2. description 必须充实详细：第一句说明异常情况和涉及的具体项目/客户/金额；第二句逐条引用明细数据（项目名、里程碑名、逾期天数、金额、风险等级），指出差异；第三句说明可能的风险和资金后果；第四至五句给出具体的下一步行动建议和处置策略。"
    "3. 当输入包含 📋 明细数据时，必须在 description 中逐条引用：分别说明每笔的项目名、客户名、里程碑、金额、逾期天数和客户风险等级。禁止只说'最大逾期X天'或总金额——必须让管理者清楚看到每笔明细的差异。"
    "4. 客户风险等级必须使用中文：normal=正常、low=低、medium=中、elevated=较高、high=高。禁止使用英文原值。"
    "5. 语气专业、务实且直接，避免空话套话或解释。"
    "6. 严格输出纯 JSON 数组，不要 markdown fence 或任何前缀正文。"
)

ENHANCE_USER_PROMPT = "以下是检测到的业务异常（共 {count} 条），请逐条改写：\n{rule_text}\n\n历史决策参考：\n{feedback_text}\n\n请输出 JSON 数组，数组长度必须与输入条数相同。"

ENHANCE_RETRY_SYSTEM_PROMPT = (
    '请仅输出纯 JSON 数组，禁止输出 markdown、注释或其他文字。'
    '格式示例：[{"title": "标题", "description": "详细描述"}]'
)

ENHANCE_RETRY_USER_PROMPT = "请仅返回 JSON 数组（{count} 个元素），改写以下业务异常：\n{rule_text}"


class BaseLLMProvider(ABC):
    """LLM Provider 抽象基类。"""

    @abstractmethod
    async def enhance(self, rule_text: str, feedback_text: str = "") -> Optional[List[Dict[str, Any]]]:
        """对规则引擎输出进行语言增强，返回改写后的建议列表。"""
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        """返回当前模型名称。"""
        ...


class NullProvider(BaseLLMProvider):
    """none 档——不做任何 LLM 调用，直接返回 None（降级为规则文本）。"""

    async def enhance(self, rule_text: str, feedback_text: str = "") -> Optional[List[Dict[str, Any]]]:
        return None

    def get_model_name(self) -> str:
        return "none"


class OllamaProvider(BaseLLMProvider):
    """local 档——通过 Ollama HTTP API 调用。"""

    def __init__(self, model: str, base_url: str):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def get_model_name(self) -> str:
        return f"local:{self.model}"

    async def enhance(self, rule_text: str, feedback_text: str = "") -> Optional[List[Dict[str, Any]]]:
        count = rule_text.count('"index"') or rule_text.count('\n- ')
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": ENHANCE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": ENHANCE_USER_PROMPT.format(
                        rule_text=rule_text,
                        feedback_text=feedback_text,
                        count=count or 1,
                    ),
                },
            ],
            "stream": False,
            "options": {"temperature": 0.75},
        }
        try:
            logger.info(f"Ollama 请求 model=%s, rule_text长度=%d", self.model, len(rule_text))
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
            content = data.get("message", {}).get("content", "")
            logger.info(f"Ollama 返回: %.200s", content)
            result = _try_parse_llm_json(content)
            if result is not None:
                return result
            # 重试一次
            return await self._retry(rule_text)
        except Exception as e:
            logger.warning("Ollama 调用失败: %s", e)
            return None

    async def _retry(self, rule_text: str) -> Optional[List[Dict[str, Any]]]:
        count = rule_text.count('"index"') or 1
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": ENHANCE_RETRY_SYSTEM_PROMPT},
                {"role": "user", "content": ENHANCE_RETRY_USER_PROMPT.format(rule_text=rule_text, count=count)},
            ],
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
            content = data.get("message", {}).get("content", "")
            return _try_parse_llm_json(content)
        except Exception as e:
            logger.warning("Ollama 重试失败: %s", e)
            return None


class ExternalAPIProvider(BaseLLMProvider):
    """api 档——OpenAI 兼容接口。"""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def get_model_name(self) -> str:
        return f"api:{self.model}"

    def is_available(self) -> bool:
        """检查 API Provider 是否可用（有 key 和 base_url）。"""
        return bool(self.api_key and self.base_url)

    async def call_freeform(self, messages: list) -> Optional[str]:
        """自由问答调用，返回模型原始文本。"""
        payload = {"model": self.model, "messages": messages}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions", json=payload, headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            logger.warning("call_freeform 失败: %s", e)
            return None

    async def _call_llm_single_var(
        self, var_name: str, context: dict, prompt: str,
    ) -> Optional[str]:
        """针对单个报告变量生成文本。"""
        context_str = json.dumps(context, ensure_ascii=False, default=str)
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一位资深经营顾问，请基于以下经营数据回答问题。"
                    "只输出分析文本，不要输出 JSON 或其他格式。\n\n"
                    f"经营数据：\n{context_str}"
                ),
            },
            {"role": "user", "content": prompt},
        ]
        payload = {"model": self.model, "messages": messages}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions", json=payload, headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            logger.warning("_call_llm_single_var 失败 | var=%s | error=%s", var_name, e)
            return None

    async def enhance(self, rule_text: str, feedback_text: str = "") -> Optional[List[Dict[str, Any]]]:
        count = rule_text.count('"index"') or 1
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": ENHANCE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": ENHANCE_USER_PROMPT.format(
                        rule_text=rule_text,
                        feedback_text=feedback_text,
                        count=count,
                    ),
                },
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
                resp = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            result = _try_parse_llm_json(content)
            if result is not None:
                return result
            return await self._retry(rule_text, headers)
        except Exception as e:
            logger.warning("外部 API 服务不可用: %s", e)
            return None

    async def _retry(self, rule_text: str, headers: dict) -> Optional[List[Dict[str, Any]]]:
        count = rule_text.count('"index"') or 1
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": ENHANCE_RETRY_SYSTEM_PROMPT},
                {"role": "user", "content": ENHANCE_RETRY_USER_PROMPT.format(rule_text=rule_text, count=count)},
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
                resp = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return _try_parse_llm_json(content)
        except Exception as e:
            logger.warning("外部 API 重试失败: %s", e)
            return None


def _try_parse_llm_json(content: str) -> Optional[List[Dict[str, Any]]]:
    """三步解析策略：直接解析 → 正则提取括号 → 返回 None。"""
    if not content or not content.strip():
        return None

    # Step 1: 直接解析
    try:
        result = json.loads(content)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # Step 2: 正则提取最外层 [...]
    match = re.search(r"\[.*\]", content, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    # Step 3: 解析失败，触发重试
    logger.warning("LLM 返回内容无法解析为 JSON: %.100s", content)
    return None


def get_llm_provider(config: Optional[dict] = None) -> BaseLLMProvider:
    from app.core.constants import LLM_PROVIDER_NONE, LLM_PROVIDER_LOCAL, LLM_PROVIDER_API

    if config:
        provider = config.get("provider") or LLM_PROVIDER_NONE
    else:
        # 优先从环境变量读取，其次用 settings
        from app.config import settings
        provider = os.environ.get("LLM_PROVIDER") or getattr(settings, "LLM_PROVIDER", LLM_PROVIDER_NONE)

    provider = provider.lower() if provider else LLM_PROVIDER_NONE

    if provider == LLM_PROVIDER_LOCAL:
        if config:
            model = config.get("local_model") or "gemma4:e2b:q4"
            base_url = config.get("local_base_url") or "http://localhost:11434"
        else:
            from app.config import settings
            model = getattr(settings, "LLM_LOCAL_MODEL", None) or "gemma4:e2b:q4"
            base_url = os.environ.get("LLM_LOCAL_BASE_URL", None) or "http://localhost:11434"
        return OllamaProvider(model=model, base_url=base_url)

    if provider == LLM_PROVIDER_API:
        if config:
            api_key = config.get("api_key") or ""
            base_url = config.get("api_base") or "https://api.openai.com/v1"
            model = config.get("api_model") or "gpt-4o-mini"
        else:
            api_key = os.environ.get("LLM_API_KEY", "")
            base_url = os.environ.get("LLM_API_BASE", "https://api.openai.com/v1")
            model = os.environ.get("LLM_API_MODEL", "gpt-4o-mini")
        return ExternalAPIProvider(api_key=api_key, base_url=base_url, model=model)

    return NullProvider()


def build_llm_context(
    rules_output: List[Dict[str, Any]],
    feedback_records: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, str]:
    """构建 LLM 上下文（含反馈聚合去重）。

    只向 LLM 发送精简字段（index/title/description/priority），
    避免内部字段（action_params、source_rule 等）干扰小模型生成。
    当 data 中包含 details 明细时，将其格式化为可读文本注入 description。
    """
    if rules_output:
        simplified = []
        for i, item in enumerate(rules_output):
            raw_params = item.get("action_params")
            if isinstance(raw_params, str):
                try:
                    raw_params = json.loads(raw_params)
                except Exception:
                    raw_params = {}
            if not isinstance(raw_params, dict):
                raw_params = {}

            # 从 data 字段提取 details 明细并格式化为可读文本
            raw_data = item.get("data")
            details_text = ""
            if isinstance(raw_data, str):
                try:
                    raw_data = json.loads(raw_data)
                except Exception:
                    raw_data = {}
            if isinstance(raw_data, dict):
                details = raw_data.get("details")
                if isinstance(details, list) and details:
                    lines = []
                    for d in details:
                        proj = d.get("project_name", "未知项目")
                        cust = d.get("customer_name", "")
                        ms = d.get("title", "")
                        amt = d.get("amount", 0)
                        days = d.get("days_overdue", 0)
                        risk = d.get("customer_risk_level", "normal")
                        risk_label = {"normal": "正常", "low": "低", "medium": "中", "elevated": "较高", "high": "高"}.get(risk, risk)
                        lines.append(
                            f"  - 项目：{proj} | 客户：{cust} | 里程碑：{ms} | "
                            f"金额：¥{amt:,.2f} | 逾期：{days} 天 | 客户风险：{risk_label}"
                        )
                    details_text = "\n\n📋 明细数据：\n" + "\n".join(lines)

            simplified.append({
                "index": i,
                "decision_type": item.get("decision_type", ""),
                "suggestion_type": item.get("suggestion_type", ""),
                "priority": item.get("priority", "medium"),
                "title": item.get("title", ""),
                "description": item.get("description", "") + details_text,
                "data": {k: v for k, v in raw_params.items() if not k.endswith("_id") and k != "id"},
            })
        rule_text = json.dumps(simplified, ensure_ascii=False, indent=2)
    else:
        rule_text = "无异常检测"

    feedback_lines: List[str] = []
    if feedback_records:
        seen: set = set()
        deduped = []
        for rec in feedback_records[-FEEDBACK_CONTEXT_MAX_RECORDS:]:
            key = (rec.get("decision_type", ""), rec.get("suggestion_type", ""))
            if key not in seen:
                seen.add(key)
                deduped.append(rec)

        for rec in deduped:
            weight = _calc_feedback_weight(rec)
            feedback_lines.append(
                f"- [{rec.get('decision_type', '?')}/{rec.get('suggestion_type', '?')}] "
                f"用户决策: {rec.get('decision_type', '?')}, "
                f"权重: {weight}"
            )

    feedback_text = "\n".join(feedback_lines) if feedback_lines else "无历史反馈记录"

    return {
        "rule_text": rule_text,
        "feedback_text": feedback_text,
    }


def _calc_feedback_weight(record: Dict[str, Any]) -> int:
    """计算单条反馈记录的权重。"""
    weight = 0
    for field, w in FEEDBACK_WEIGHT_RULES.items():
        if record.get(field):
            weight += w
    return weight
