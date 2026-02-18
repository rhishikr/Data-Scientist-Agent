from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .blackboard import SharedBlackboard


class AgentStatus(str, Enum):
    IDLE = "idle"
    PERCEIVING = "perceiving"
    REASONING = "reasoning"
    ACTING = "acting"
    COMPLETE = "complete"
    ERROR = "error"


class MessageType(str, Enum):
    DATA_READY = "data_ready"
    AGENT_COMPLETE = "agent_complete"
    AGENT_ERROR = "agent_error"
    LLM_DECISION = "llm_decision"
    STATUS_UPDATE = "status_update"


@dataclass
class AgentMessage:
    """Inter-agent communication unit."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    sender: str = ""
    recipient: str = ""
    msg_type: MessageType = MessageType.STATUS_UPDATE
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["msg_type"] = self.msg_type.value
        return d


@dataclass
class AgentResult:
    """Standardized result from any agent's act() phase."""

    agent_id: str
    success: bool
    outputs: Dict[str, Any] = field(default_factory=dict)
    llm_reasoning: Optional[str] = None
    llm_decisions: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    error: Optional[str] = None
    messages: List[AgentMessage] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["messages"] = [
            m.to_dict() if isinstance(m, AgentMessage) else m for m in self.messages
        ]
        return d


class BaseAgent(ABC):
    """
    Abstract base for all pipeline agents.

    Each agent follows the Perceive -> Reason -> Act cycle:

    - perceive(): Examine the blackboard/environment, gather inputs
    - reason():   Use LLM to make decisions about HOW to execute
    - act():      Execute the actual pipeline logic (wrapping existing code)
    """

    def __init__(self, agent_id: str, name: str, description: str):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.status = AgentStatus.IDLE
        self._log: List[AgentMessage] = []

    def log(
        self,
        msg_type: MessageType,
        payload: Dict[str, Any],
        recipient: str = "orchestrator",
    ) -> AgentMessage:
        msg = AgentMessage(
            sender=self.agent_id,
            recipient=recipient,
            msg_type=msg_type,
            payload=payload,
        )
        self._log.append(msg)
        return msg

    @abstractmethod
    async def perceive(self, blackboard: "SharedBlackboard") -> Dict[str, Any]:
        """Examine the shared state. Return a summary of inputs and context."""
        ...

    @abstractmethod
    async def reason(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """Use an LLM to decide strategy/parameters for the act() phase."""
        ...

    @abstractmethod
    async def act(
        self, plan: Dict[str, Any], blackboard: "SharedBlackboard"
    ) -> AgentResult:
        """Execute the actual pipeline work. Write results to the blackboard."""
        ...

    async def run(self, blackboard: "SharedBlackboard") -> AgentResult:
        """Full perceive -> reason -> act cycle."""
        import time

        start = time.time()
        self._log = []

        try:
            self.status = AgentStatus.PERCEIVING
            self.log(
                MessageType.STATUS_UPDATE,
                {"status": "perceiving", "agent": self.name},
            )
            perception = await self.perceive(blackboard)

            self.status = AgentStatus.REASONING
            self.log(
                MessageType.STATUS_UPDATE,
                {"status": "reasoning", "agent": self.name},
            )
            plan = await self.reason(perception)

            self.status = AgentStatus.ACTING
            self.log(
                MessageType.STATUS_UPDATE,
                {"status": "acting", "agent": self.name},
            )
            result = await self.act(plan, blackboard)

            self.status = AgentStatus.COMPLETE
            result.duration_seconds = time.time() - start
            result.messages = list(self._log)

            self.log(
                MessageType.AGENT_COMPLETE,
                {"agent": self.name, "success": result.success},
            )
            return result

        except Exception as e:
            self.status = AgentStatus.ERROR
            self.log(
                MessageType.AGENT_ERROR,
                {"agent": self.name, "error": str(e)},
            )
            return AgentResult(
                agent_id=self.agent_id,
                success=False,
                error=str(e),
                duration_seconds=time.time() - start,
                messages=list(self._log),
            )
