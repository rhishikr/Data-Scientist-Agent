from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .base import AgentMessage, AgentResult


@dataclass
class SharedBlackboard:
    """
    Central shared state for inter-agent communication.

    Each agent reads from and writes to sections of this blackboard.
    Implements the blackboard architectural pattern — a well-known
    multi-agent communication mechanism from AI literature.
    """

    # Pipeline configuration
    config: Dict[str, Any] = field(
        default_factory=lambda: {"reset": True, "alpha": 0.05}
    )

    # Directory paths
    paths: Dict[str, str] = field(default_factory=dict)

    # Data state: each agent writes output metadata here; downstream agents read it
    data_state: Dict[str, Any] = field(default_factory=dict)

    # LLM decisions log (for transparency / academic demonstration)
    llm_decisions: List[Dict[str, Any]] = field(default_factory=list)

    # Agent execution results
    agent_results: Dict[str, AgentResult] = field(default_factory=dict)

    # Message bus (all inter-agent messages)
    messages: List[AgentMessage] = field(default_factory=list)

    # Event callbacks (for real-time frontend updates via SSE)
    _listeners: List[Callable[[AgentMessage], None]] = field(
        default_factory=list, repr=False
    )

    def post_message(self, msg: AgentMessage) -> None:
        self.messages.append(msg)
        for listener in self._listeners:
            try:
                listener(msg)
            except Exception:
                pass

    def add_listener(self, callback: Callable[[AgentMessage], None]) -> None:
        self._listeners.append(callback)

    def set_agent_result(self, agent_id: str, result: AgentResult) -> None:
        self.agent_results[agent_id] = result

    def get_agent_result(self, agent_id: str) -> Optional[AgentResult]:
        return self.agent_results.get(agent_id)

    def to_status_dict(self) -> Dict[str, Any]:
        """Snapshot for the /api/pipeline/status endpoint."""
        return {
            "agents": {
                aid: {
                    "success": r.success,
                    "duration": r.duration_seconds,
                    "llm_reasoning": r.llm_reasoning,
                    "llm_decisions": r.llm_decisions,
                    "error": r.error,
                }
                for aid, r in self.agent_results.items()
            },
            "llm_decisions": self.llm_decisions,
            "messages": [m.to_dict() for m in self.messages[-50:]],
        }
