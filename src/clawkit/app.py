"""Composition root for the local ClawKit runtime."""

from __future__ import annotations

from clawkit import __version__
from clawkit.auth import authentication_status
from clawkit.audit import AuditLogger
from clawkit.bridge.job_store import PersistentJobStore
from clawkit.bridge.runtime import OffsetStore, TelegramBridge
from clawkit.bridge.telegram_client import TelegramClient
from clawkit.config import ConfigurationError, load_runtime_settings
from clawkit.context import build_instance_context
from clawkit.instance import load_instance
from clawkit.module_system import ModuleManager
from clawkit.onboarding import OnboardingRouter, OnboardingStore
from clawkit.paths import ClawKitPaths
from clawkit.reminders import ReminderEngine
from clawkit.router.agents import ClaudeAdapter, CodexAdapter
from clawkit.router.router import AgentRouter
from clawkit.router.state import RouterStateStore
from clawkit.skills import sync_skill_discovery
from clawkit.updater import DEFAULT_REPOSITORY, UpdateNotificationEngine


def _positive_int(value: str, *, name: str, default: int) -> int:
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if parsed < 10 or parsed > 7200:
        raise ConfigurationError(f"{name} must be between 10 and 7200")
    return parsed


def build_bridge(paths: ClawKitPaths) -> TelegramBridge:
    sync_skill_discovery(paths)
    instance = load_instance(paths.instance_dir / "instance.yaml")
    runtime = load_runtime_settings(
        paths,
        required_names=("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"),
    )
    try:
        chat_id = int(runtime.require("TELEGRAM_CHAT_ID"))
    except ValueError as exc:
        raise ConfigurationError("TELEGRAM_CHAT_ID must be an integer") from exc
    if chat_id == 0:
        raise ConfigurationError("TELEGRAM_CHAT_ID must not be zero")
    timeout = _positive_int(
        runtime.get("CLAWKIT_AGENT_TIMEOUT_SECONDS"),
        name="CLAWKIT_AGENT_TIMEOUT_SECONDS",
        default=900,
    )
    audit = AuditLogger(paths.audit_log_file)
    modules = ModuleManager(paths, runtime, instance)
    preferred = instance.preferred_agent
    if preferred == "auto":
        if authentication_status(paths, "claude").authenticated:
            preferred = "claude"
        elif authentication_status(paths, "codex").authenticated:
            preferred = "codex"
    router = AgentRouter(
        claude=ClaudeAdapter(
            paths,
            model=runtime.get("CLAWKIT_CLAUDE_MODEL"),
            timeout_seconds=timeout,
        ),
        codex=CodexAdapter(
            paths,
            model=runtime.get("CLAWKIT_CODEX_MODEL"),
            reasoning_effort=runtime.get("CLAWKIT_CODEX_REASONING_EFFORT"),
            timeout_seconds=timeout,
        ),
        state_store=RouterStateStore(paths.router_state_file),
        audit=audit,
        preferred_agent=preferred,
        language=instance.language,
        context_provider=lambda: _combined_context(paths, instance.timezone, modules),
    )
    onboarding = OnboardingRouter(
        inner=router,
        store=OnboardingStore(paths.onboarding_state_file),
        settings=instance,
    )
    reminders = ReminderEngine(
        reminders_file=paths.instance_dir / "reminders.md",
        state_file=paths.reminder_state_file,
        timezone=instance.timezone,
        language=instance.language,
    )
    updates = UpdateNotificationEngine(
        state_file=paths.update_state_file,
        repository=runtime.get("CLAWKIT_UPDATE_REPOSITORY") or DEFAULT_REPOSITORY,
        current_version=__version__,
        token=runtime.get("CLAWKIT_GITHUB_TOKEN"),
        enabled=runtime.get("CLAWKIT_UPDATE_CHECK", "1") != "0",
        language=instance.language,
    )
    return TelegramBridge(
        client=TelegramClient(runtime.require("TELEGRAM_BOT_TOKEN")),
        router=onboarding,
        allowed_chat_id=chat_id,
        offset_store=OffsetStore(paths.telegram_offset_file),
        audit=audit,
        language=instance.language,
        opening_message=onboarding.open_conversation,
        opening_delivered=onboarding.mark_opening_sent,
        job_store=PersistentJobStore(paths.queue_dir),
        scheduled_notifications=lambda: [
            *reminders.pending(),
            *updates.pending(),
            *modules.pending_notifications(),
        ],
        scheduled_delivered=lambda key: (
            reminders.mark_sent(key)
            if key.startswith("reminder:")
            else updates.mark_sent(key)
            if key.startswith("update:")
            else modules.mark_notification_sent(key)
        ),
    )


def _combined_context(
    paths: ClawKitPaths,
    timezone: str,
    modules: ModuleManager,
) -> str:
    base = build_instance_context(paths, timezone=timezone)
    extension = modules.context()
    if not extension:
        return base
    return f"{base}\n\n<clawkit_module_context>\n{extension}\n</clawkit_module_context>"
