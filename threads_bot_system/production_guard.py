"""Production safety guard for Threads publish automation.

This module enforces the production safety rules defined in PRODUCTION_SAFETY.md.
It acts as the single choke-point before any real Threads API call.

Design principle: deny by default. Only allow when all conditions are explicitly met.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable


# ---------------------------------------------------------------------------
# Defaults — all deny production
# ---------------------------------------------------------------------------

DEFAULT_ENV = "development"
DEFAULT_PUBLISH_ENABLED = False
DEFAULT_DRY_RUN = True
DEFAULT_MAX_DAILY_POSTS = 10
DEFAULT_MIN_POST_INTERVAL_MINUTES = 10
DEFAULT_MAX_CONSECUTIVE_FAILURES = 1
DEFAULT_MAX_CONSECUTIVE_UNKNOWN = 1


# ---------------------------------------------------------------------------
# Content rejection patterns — deterministic, not AI
# ---------------------------------------------------------------------------

# Matches content that is purely digits (possibly with whitespace)
_RE_DIGITS_ONLY = re.compile(r"^\s*\d+\s*$")

# Patterns that match test-like content
_TEST_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"^\s*test\s*$",
        r"^\s*testing\s*$",
        r"^\s*hello\s*$",
        r"^\s*hi\s*$",
        r"^\s*测试\s*$",
        r"^\s*测试发布\s*$",
        r"^\s*test\s*post\s*$",
        r"^\s*test\s*thread\s*$",
    ]
]


# ---------------------------------------------------------------------------
# Guard configuration
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ProductionGuardConfig:
    """All configurable safety limits for production publishing."""

    env: str = DEFAULT_ENV
    publish_enabled: bool = DEFAULT_PUBLISH_ENABLED
    dry_run: bool = DEFAULT_DRY_RUN
    max_daily_posts: int = DEFAULT_MAX_DAILY_POSTS
    min_post_interval_minutes: int = DEFAULT_MIN_POST_INTERVAL_MINUTES
    max_consecutive_failures: int = DEFAULT_MAX_CONSECUTIVE_FAILURES
    max_consecutive_unknown: int = DEFAULT_MAX_CONSECUTIVE_UNKNOWN

    @classmethod
    def from_env(cls, env_dict: dict[str, str] | None = None) -> "ProductionGuardConfig":
        """Build config from environment variables with safe defaults."""
        src = env_dict if env_dict is not None else os.environ
        return cls(
            env=src.get("ENV", DEFAULT_ENV).strip().lower() or DEFAULT_ENV,
            publish_enabled=_parse_bool(src.get("PUBLISH_ENABLED"), DEFAULT_PUBLISH_ENABLED),
            dry_run=_parse_bool(src.get("DRY_RUN"), DEFAULT_DRY_RUN),
            max_daily_posts=_parse_int(src.get("MAX_DAILY_POSTS"), DEFAULT_MAX_DAILY_POSTS),
            min_post_interval_minutes=_parse_int(
                src.get("MIN_POST_INTERVAL_MINUTES"), DEFAULT_MIN_POST_INTERVAL_MINUTES
            ),
            max_consecutive_failures=_parse_int(
                src.get("MAX_CONSECUTIVE_FAILURES"), DEFAULT_MAX_CONSECUTIVE_FAILURES
            ),
            max_consecutive_unknown=_parse_int(
                src.get("MAX_CONSECUTIVE_UNKNOWN"), DEFAULT_MAX_CONSECUTIVE_UNKNOWN
            ),
        )

    @property
    def is_production(self) -> bool:
        """Return True only when ALL three production gates are open."""
        return self.env == "production" and self.publish_enabled and not self.dry_run


# ---------------------------------------------------------------------------
# Guard result types
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class GuardDecision:
    """Result of a production safety check."""

    allowed: bool
    reason: str


# ---------------------------------------------------------------------------
# Content guard
# ---------------------------------------------------------------------------


def guard_content(text: str) -> GuardDecision:
    """Check whether content is safe for production publishing.

    Rejects content that is empty, purely numeric, or matches known test patterns.
    Accepts content that passes all deterministic checks.
    """
    stripped = text.strip()

    if not stripped:
        return GuardDecision(allowed=False, reason="content_is_empty")

    if _RE_DIGITS_ONLY.match(stripped):
        return GuardDecision(allowed=False, reason="content_is_pure_digits")

    if len(stripped) < 10:
        return GuardDecision(allowed=False, reason="content_too_short")

    for pattern in _TEST_PATTERNS:
        if pattern.match(stripped):
            return GuardDecision(allowed=False, reason=f"content_matches_test_pattern")

    return GuardDecision(allowed=True, reason="ok")


# ---------------------------------------------------------------------------
# Duplicate guard
# ---------------------------------------------------------------------------


def guard_duplicate(text: str, recent_texts: Iterable[str]) -> GuardDecision:
    """Reject content that is identical to recently published content."""
    normalized = text.strip()
    for recent in recent_texts:
        if normalized == recent.strip():
            return GuardDecision(allowed=False, reason="content_is_duplicate")
    return GuardDecision(allowed=True, reason="ok")


# ---------------------------------------------------------------------------
# Content ID reuse guard
# ---------------------------------------------------------------------------


def guard_content_id_reuse(content_id: str, published_ids: Iterable[str]) -> GuardDecision:
    """Reject a content_id that has already been published."""
    if content_id in published_ids:
        return GuardDecision(allowed=False, reason="content_id_already_published")
    return GuardDecision(allowed=True, reason="ok")


# ---------------------------------------------------------------------------
# Rate / budget guard
# ---------------------------------------------------------------------------


def guard_daily_limit(todays_post_count: int, max_daily: int) -> GuardDecision:
    """Reject if today's post count has reached the daily limit."""
    if todays_post_count >= max_daily:
        return GuardDecision(
            allowed=False,
            reason=f"daily_limit_reached ({todays_post_count}/{max_daily})",
        )
    return GuardDecision(allowed=True, reason="ok")


def guard_post_interval(
    last_publish_time: str | None, min_interval_minutes: int
) -> GuardDecision:
    """Reject if minimum post interval has not elapsed since last publish."""
    if last_publish_time is None:
        return GuardDecision(allowed=True, reason="ok")

    try:
        last = datetime.fromisoformat(last_publish_time.replace("Z", "+00:00"))
    except ValueError:
        return GuardDecision(allowed=True, reason="ok")

    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)

    elapsed = datetime.now(timezone.utc) - last.astimezone(timezone.utc)
    minimum_seconds = min_interval_minutes * 60

    if elapsed.total_seconds() < minimum_seconds:
        remaining = int(minimum_seconds - elapsed.total_seconds())
        return GuardDecision(
            allowed=False,
            reason=f"post_interval_not_elapsed (need {remaining}s more)",
        )

    return GuardDecision(allowed=True, reason="ok")


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------


def guard_consecutive_failures(
    consecutive_failures: int, max_allowed: int
) -> GuardDecision:
    """Trip if consecutive failure count exceeds threshold."""
    if consecutive_failures > max_allowed:
        return GuardDecision(
            allowed=False,
            reason=f"circuit_breaker_tripped: consecutive_failures={consecutive_failures}",
        )
    return GuardDecision(allowed=True, reason="ok")


def guard_consecutive_unknown(
    consecutive_unknown: int, max_allowed: int
) -> GuardDecision:
    """Trip if consecutive unknown count exceeds threshold."""
    if consecutive_unknown > max_allowed:
        return GuardDecision(
            allowed=False,
            reason=f"circuit_breaker_tripped: consecutive_unknown={consecutive_unknown}",
        )
    return GuardDecision(allowed=True, reason="ok")


# ---------------------------------------------------------------------------
# Composite guard — the single entry point for pre-publish checks
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class PrePublishReport:
    """Full pre-publish safety check report."""

    allowed: bool
    mode: str  # "production", "dry_run", or "blocked"
    decisions: list[GuardDecision] = field(default_factory=list)

    @property
    def would_publish(self) -> bool:
        """True if this would result in a real Threads post."""
        return self.allowed and self.mode == "production"

    @property
    def is_dry_run(self) -> bool:
        """True if the system is in dry-run mode."""
        return self.mode == "dry_run"


def pre_publish_check(
    text: str,
    content_id: str,
    config: ProductionGuardConfig,
    *,
    published_content_ids: Iterable[str] = (),
    recent_texts: Iterable[str] = (),
    todays_post_count: int = 0,
    last_publish_time: str | None = None,
    consecutive_failures: int = 0,
    consecutive_unknown: int = 0,
) -> PrePublishReport:
    """Run all production safety checks before publishing.

    This is the SINGLE entry point that must be called before any
    real Threads publish attempt. Returns a report indicating whether
    publishing is allowed, and if so, in what mode.
    """
    decisions: list[GuardDecision] = []

    # Content quality checks run in ALL modes
    for guard_fn in [guard_content]:
        d = guard_fn(text)
        decisions.append(d)
        if not d.allowed:
            return PrePublishReport(allowed=False, mode="blocked", decisions=decisions)

    # Duplicate checks
    d = guard_duplicate(text, recent_texts)
    decisions.append(d)
    if not d.allowed:
        return PrePublishReport(allowed=False, mode="blocked", decisions=decisions)

    d = guard_content_id_reuse(content_id, published_content_ids)
    decisions.append(d)
    if not d.allowed:
        return PrePublishReport(allowed=False, mode="blocked", decisions=decisions)

    # If not in production mode, allow dry-run
    if not config.is_production:
        return PrePublishReport(allowed=True, mode="dry_run", decisions=decisions)

    # Production-mode checks
    for guard_fn, kwargs in [
        (guard_daily_limit, {"todays_post_count": todays_post_count, "max_daily": config.max_daily_posts}),
        (guard_post_interval, {"last_publish_time": last_publish_time, "min_interval_minutes": config.min_post_interval_minutes}),
        (guard_consecutive_failures, {"consecutive_failures": consecutive_failures, "max_allowed": config.max_consecutive_failures}),
        (guard_consecutive_unknown, {"consecutive_unknown": consecutive_unknown, "max_allowed": config.max_consecutive_unknown}),
    ]:
        d = guard_fn(**kwargs)
        decisions.append(d)
        if not d.allowed:
            return PrePublishReport(allowed=False, mode="blocked", decisions=decisions)

    return PrePublishReport(allowed=True, mode="production", decisions=decisions)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes"}


def _parse_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value.strip())
    except (ValueError, TypeError):
        return default
