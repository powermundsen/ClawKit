"""Explicit, disabled-by-default extension points for local ClawKit modules."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Protocol

from clawkit.config import ConfigurationError, RuntimeSettings
from clawkit.instance import InstanceSettings
from clawkit.paths import ClawKitPaths

_MODULE_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


@dataclass(frozen=True, slots=True)
class ModuleHealth:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True, slots=True)
class ModuleNotification:
    key: str
    text: str


class ClawKitModule(Protocol):
    name: str

    def context(self) -> str: ...

    def health(self) -> list[ModuleHealth]: ...

    def run_scheduled(self, now: datetime) -> None: ...

    def pending_notifications(self) -> list[ModuleNotification]: ...

    def mark_notification_sent(self, key: str) -> None: ...


def parse_enabled_modules(value: str) -> tuple[str, ...]:
    if not value.strip():
        return ()
    names = tuple(part.strip() for part in value.split(",") if part.strip())
    if any(not _MODULE_RE.fullmatch(name) for name in names):
        raise ConfigurationError("CLAWKIT_MODULES contains an invalid module name")
    if len(set(names)) != len(names):
        raise ConfigurationError("CLAWKIT_MODULES contains duplicates")
    unknown = sorted(set(names) - {"local-health"})
    if unknown:
        raise ConfigurationError(f"unknown ClawKit modules: {', '.join(unknown)}")
    return names


class ModuleManager:
    def __init__(
        self,
        paths: ClawKitPaths,
        runtime: RuntimeSettings,
        instance: InstanceSettings,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.paths = paths
        self.runtime = runtime
        self.instance = instance
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.enabled_names = parse_enabled_modules(runtime.get("CLAWKIT_MODULES"))
        self.modules: list[ClawKitModule] = []
        for name in self.enabled_names:
            if name == "local-health":
                from clawkit.modules.local_health import LocalHealthModule

                self.modules.append(LocalHealthModule(paths, instance))

    def context(self) -> str:
        sections: list[str] = []
        for module in self.modules:
            text = module.context().strip()
            if text:
                sections.append(f"## Module: {module.name}\n{text}")
        return "\n\n".join(sections)[:32_000]

    def health(self) -> list[ModuleHealth]:
        checks: list[ModuleHealth] = []
        for module in self.modules:
            checks.extend(module.health())
        return checks

    def pending_notifications(self) -> list[ModuleNotification]:
        notifications: list[ModuleNotification] = []
        clock = self.now()
        if clock.tzinfo is None:
            clock = clock.replace(tzinfo=timezone.utc)
        for module in self.modules:
            module.run_scheduled(clock.astimezone(timezone.utc))
            notifications.extend(module.pending_notifications())
        return notifications

    def mark_notification_sent(self, key: str) -> None:
        prefix = key.split(":", 1)[0]
        for module in self.modules:
            if module.name == prefix:
                module.mark_notification_sent(key)
                return
        raise ValueError("notification does not belong to an enabled module")

    def require(self, name: str) -> ClawKitModule:
        for module in self.modules:
            if module.name == name:
                return module
        raise ConfigurationError(
            f"module {name} is disabled; add it to CLAWKIT_MODULES in runtime.env"
        )
