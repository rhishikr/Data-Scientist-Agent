from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional


# Lazy imports to avoid crashing if langchain is not yet installed.
# The actual imports happen at first use.
_llm: Optional[Any] = None


def get_llm(model: str = os.getenv("RAG_LLM_MODEL", "gpt-4.1-mini"), temperature: float = 0.2) -> Any:
    from langchain_openai import ChatOpenAI

    global _llm
    if _llm is None or _llm.model_name != model:
        _llm = ChatOpenAI(model=model, temperature=temperature)
    return _llm


async def ask_llm(
    system_prompt: str,
    user_prompt: str,
    model: str = os.getenv("RAG_LLM_MODEL", "gpt-4.1-mini"),
) -> str:
    """
    Async wrapper for LLM calls across all agents.
    All agent reasoning goes through this function.
    """
    from langchain_core.messages import SystemMessage, HumanMessage

    llm = get_llm(model=model)
    response = await llm.ainvoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )
    return response.content


def parse_llm_json(raw: str, fallback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Parse JSON from LLM response, stripping markdown code fences if present."""
    text = raw.strip()
    match = re.match(r"^```(?:json)?\s*\n?(.*?)```\s*$", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if fallback is not None:
            return fallback
        return {"assessment": raw[:200], "proceed": True}
