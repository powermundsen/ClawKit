"""Minimal dual-agent orchestration with explicit modes and safe fallback."""

from __future__ import annotations

from collections.abc import Callable
from threading import Event, RLock
from typing import Protocol

from clawkit.audit import AuditLogger
from clawkit.router.models import AgentResponse, RouterMode, RouterState
from clawkit.router.state import RouterStateStore


class AgentAdapter(Protocol):
    name: str

    def call(
        self,
        message: str,
        *,
        session_id: str = "",
        cancel_event: Event | None = None,
    ) -> AgentResponse: ...


def _user_error(category: str, language: str) -> str:
    norwegian = not language.lower().startswith("en")
    messages = {
        "cancelled": (
            "Jobben ble stoppet."
            if norwegian
            else "The active job was stopped."
        ),
        "timeout": (
            "Agenten brukte for lang tid. Prøv igjen."
            if norwegian
            else "The agent timed out. Please try again."
        ),
        "auth": (
            "Agenten må logges inn på nytt. Kjør `clawkit auth` lokalt."
            if norwegian
            else "The agent must sign in again. Run `clawkit auth` locally."
        ),
        "binary_missing": (
            "En agent mangler. Kjør ClawKit-installeren på nytt lokalt."
            if norwegian
            else "An agent is missing. Run the ClawKit installer again locally."
        ),
    }
    return messages.get(
        category,
        (
            "Det oppsto en teknisk agentfeil. Detaljene er logget lokalt."
            if norwegian
            else "A technical agent error occurred. Details were logged locally."
        ),
    )


class AgentRouter:
    def __init__(
        self,
        *,
        claude: AgentAdapter,
        codex: AgentAdapter,
        state_store: RouterStateStore,
        audit: AuditLogger,
        preferred_agent: str = "auto",
        language: str = "nb",
        context_provider: Callable[[], str] | None = None,
    ) -> None:
        self.adapters = {"claude": claude, "codex": codex}
        self.state_store = state_store
        self.audit = audit
        self.language = language
        self.context_provider = context_provider
        self._lock = RLock()
        self.state = state_store.load()
        if preferred_agent in {"claude", "codex"}:
            self.preferred_agent = preferred_agent
        else:
            self.preferred_agent = "claude"

    def handle_command(self, message: str) -> str | None:
        parts = message.strip().split(maxsplit=1)
        if not parts:
            return None
        command = parts[0].lower()
        with self._lock:
            if command in {"/new", "/stop"}:
                self.state.claude_session_id = ""
                self.state.codex_session_id = ""
                self.state.last_error_category = ""
                self.state_store.save(self.state)
                self.audit.emit(
                    "router",
                    "sessions_closed" if command == "/stop" else "session_reset",
                    success=True,
                )
                if command == "/stop":
                    return self._text(
                        "Alle aktive Claude- og Codex-sesjoner er lukket.",
                        "All active Claude and Codex sessions are closed.",
                    )
                return self._text("Ny samtale startet.", "New conversation started.")
            if command in {"/auto", "/claude", "/codex"}:
                self.state.mode = RouterMode(command[1:])
                self.state_store.save(self.state)
                self.audit.emit(
                    "router",
                    "mode_changed",
                    mode=self.state.mode.value,
                    success=True,
                )
                return self._text(
                    f"Agentmodus: {self.state.mode.value}.",
                    f"Agent mode: {self.state.mode.value}.",
                )
            if command == "/status":
                return self._text(
                    (
                        f"Modus: {self.state.mode.value}. "
                        f"Siste agent: {self.state.last_agent or 'ingen'}."
                    ),
                    (
                        f"Mode: {self.state.mode.value}. "
                        f"Last agent: {self.state.last_agent or 'none'}."
                    ),
                )
        return None

    def route(
        self,
        message: str,
        *,
        cancel_event: Event | None = None,
    ) -> AgentResponse:
        command_response = self.handle_command(message)
        if command_response is not None:
            return AgentResponse(
                text=command_response,
                agent="router",
                success=True,
            )
        with self._lock:
            routed_message = message
            if self.context_provider is not None:
                context = self.context_provider().strip()
                if context:
                    routed_message = f"{context}\n\n<owner_message>\n{message}\n</owner_message>"
            mode = self.state.mode
            if mode == RouterMode.AUTO:
                order = [self.preferred_agent]
                order.append("codex" if order[0] == "claude" else "claude")
            else:
                order = [mode.value]

            last_response: AgentResponse | None = None
            for attempt, name in enumerate(order, start=1):
                session_id = (
                    self.state.claude_session_id
                    if name == "claude"
                    else self.state.codex_session_id
                )
                response = self.adapters[name].call(
                    routed_message,
                    session_id=session_id,
                    cancel_event=cancel_event,
                )
                last_response = response
                self.audit.emit(
                    "router",
                    "agent_attempt",
                    agent=name,
                    attempt=attempt,
                    success=response.success,
                    error_category=response.error_category or None,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    cached_input_tokens=response.cached_input_tokens,
                )
                if response.session_id:
                    if name == "claude":
                        self.state.claude_session_id = response.session_id
                    else:
                        self.state.codex_session_id = response.session_id
                if response.success:
                    self.state.last_agent = name
                    self.state.last_error_category = ""
                    self.state_store.save(self.state)
                    return response
                self.state.last_error_category = response.error_category
                if response.error_category == "cancelled":
                    break

            self.state_store.save(self.state)
            category = (
                last_response.error_category
                if last_response is not None
                else "provider_error"
            )
            return AgentResponse(
                text=_user_error(category, self.language),
                agent=(last_response.agent if last_response else "router"),
                success=False,
                error_category=category,
            )

    def _text(self, norwegian: str, english: str) -> str:
        return english if self.language.lower().startswith("en") else norwegian
