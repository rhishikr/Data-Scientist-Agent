from __future__ import annotations

from typing import Any, Optional


# Lazy imports to avoid crashing if langchain is not yet installed.
# The actual imports happen at first use.
_llm: Optional[Any] = None


def get_llm(model: str = "gpt-4o-mini", temperature: float = 0.2) -> Any:
    from langchain_openai import ChatOpenAI

    global _llm
    if _llm is None or _llm.model_name != model:
        _llm = ChatOpenAI(model=model, temperature=temperature)
    return _llm


async def ask_llm(
    system_prompt: str,
    user_prompt: str,
    model: str = "gpt-4o-mini",
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
