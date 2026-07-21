"""Tests for production safety guard."""

from __future__ import annotations

import unittest

from threads_bot_system.production_guard import (
    GuardDecision,
    ProductionGuardConfig,
    guard_consecutive_failures,
    guard_consecutive_unknown,
    guard_content,
    guard_content_id_reuse,
    guard_daily_limit,
    guard_duplicate,
    guard_post_interval,
    pre_publish_check,
)


class GuardContentTests(unittest.TestCase):
    """Content rejection rules."""

    def test_rejects_empty_text(self):
        self.assertFalse(guard_content("").allowed)
        self.assertFalse(guard_content("   ").allowed)

    def test_rejects_pure_digits(self):
        self.assertFalse(guard_content("123").allowed)
        self.assertFalse(guard_content("1234").allowed)
        self.assertFalse(guard_content("12345").allowed)
        self.assertFalse(guard_content("  42  ").allowed)

    def test_rejects_test_keywords(self):
        for text in ["test", "testing", "hello", "hi", "测试", "测试发布", "test post"]:
            with self.subTest(text=text):
                self.assertFalse(guard_content(text).allowed)

    def test_rejects_too_short(self):
        self.assertFalse(guard_content("ab").allowed)
        self.assertFalse(guard_content("123456789").allowed)  # 9 chars

    def test_accepts_valid_content(self):
        self.assertTrue(guard_content("Today is a beautiful day for a walk.").allowed)
        self.assertTrue(guard_content("这是一条有意义的真实内容。").allowed)

    def test_reports_reason(self):
        self.assertIn("digits", guard_content("123").reason)
        self.assertIn("empty", guard_content("").reason)
        # "testing" is 7 chars but still under 10, so too_short fires first
        self.assertIn("digits", guard_content("12345678901").reason)


class GuardDuplicateTests(unittest.TestCase):
    """Duplicate content rejection."""

    def test_rejects_exact_duplicate(self):
        self.assertFalse(guard_duplicate("Hello World", ["Hello World"]).allowed)

    def test_accepts_new_content(self):
        self.assertTrue(guard_duplicate("Hello World", ["Something else"]).allowed)

    def test_accepts_when_no_history(self):
        self.assertTrue(guard_duplicate("Hello World", []).allowed)


class GuardContentIdReuseTests(unittest.TestCase):
    """Content ID reuse rejection."""

    def test_rejects_published_id(self):
        self.assertFalse(
            guard_content_id_reuse("threads-abc-001", ["threads-abc-001"]).allowed
        )

    def test_accepts_new_id(self):
        self.assertTrue(
            guard_content_id_reuse("threads-abc-002", ["threads-abc-001"]).allowed
        )


class GuardDailyLimitTests(unittest.TestCase):
    """Daily post limit enforcement."""

    def test_blocks_when_at_limit(self):
        self.assertFalse(guard_daily_limit(1, 1).allowed)

    def test_blocks_when_over_limit(self):
        self.assertFalse(guard_daily_limit(3, 1).allowed)

    def test_allows_under_limit(self):
        self.assertTrue(guard_daily_limit(0, 1).allowed)


class GuardPostIntervalTests(unittest.TestCase):
    """Post interval enforcement."""

    def test_allows_when_no_previous_post(self):
        self.assertTrue(guard_post_interval(None, 60).allowed)

    def test_reports_reason_when_blocked(self):
        # This will always be blocked since last publish was just now
        from datetime import datetime, timezone

        now_str = datetime.now(timezone.utc).isoformat()
        result = guard_post_interval(now_str, 360)
        self.assertFalse(result.allowed)
        self.assertIn("post_interval_not_elapsed", result.reason)


class GuardCircuitBreakerTests(unittest.TestCase):
    """Circuit breaker enforcement."""

    def test_trips_on_consecutive_failures(self):
        self.assertFalse(guard_consecutive_failures(2, 1).allowed)

    def test_allows_when_under_threshold(self):
        self.assertTrue(guard_consecutive_failures(0, 1).allowed)
        self.assertTrue(guard_consecutive_failures(1, 1).allowed)

    def test_trips_on_consecutive_unknown(self):
        self.assertFalse(guard_consecutive_unknown(2, 1).allowed)

    def test_allows_when_under_threshold_unknown(self):
        self.assertTrue(guard_consecutive_unknown(0, 1).allowed)
        self.assertTrue(guard_consecutive_unknown(1, 1).allowed)


class ProductionGuardConfigTests(unittest.TestCase):
    """Config parsing from environment."""

    def test_defaults_are_safe(self):
        config = ProductionGuardConfig()
        self.assertEqual(config.env, "development")
        self.assertFalse(config.publish_enabled)
        self.assertTrue(config.dry_run)
        self.assertFalse(config.is_production)

    def test_production_requires_all_three(self):
        config = ProductionGuardConfig(env="production", publish_enabled=True, dry_run=False)
        self.assertTrue(config.is_production)

    def test_missing_one_disables_production(self):
        self.assertFalse(
            ProductionGuardConfig(env="development", publish_enabled=True, dry_run=False).is_production
        )
        self.assertFalse(
            ProductionGuardConfig(env="production", publish_enabled=False, dry_run=False).is_production
        )
        self.assertFalse(
            ProductionGuardConfig(env="production", publish_enabled=True, dry_run=True).is_production
        )

    def test_from_env_parses_values(self):
        config = ProductionGuardConfig.from_env({
            "ENV": "production",
            "PUBLISH_ENABLED": "true",
            "DRY_RUN": "false",
            "MAX_DAILY_POSTS": "3",
            "MIN_POST_INTERVAL_MINUTES": "120",
            "MAX_CONSECUTIVE_FAILURES": "2",
            "MAX_CONSECUTIVE_UNKNOWN": "2",
        })
        self.assertEqual(config.env, "production")
        self.assertTrue(config.publish_enabled)
        self.assertFalse(config.dry_run)
        self.assertEqual(config.max_daily_posts, 3)
        self.assertEqual(config.min_post_interval_minutes, 120)
        self.assertEqual(config.max_consecutive_failures, 2)
        self.assertEqual(config.max_consecutive_unknown, 2)

    def test_from_env_defaults_on_missing(self):
        config = ProductionGuardConfig.from_env({})
        self.assertEqual(config.env, "development")
        self.assertFalse(config.publish_enabled)
        self.assertTrue(config.dry_run)


class PrePublishCheckTests(unittest.TestCase):
    """Composite pre-publish check."""

    def _safe_config(self) -> ProductionGuardConfig:
        return ProductionGuardConfig(env="development", publish_enabled=False, dry_run=True)

    def _prod_config(self) -> ProductionGuardConfig:
        return ProductionGuardConfig(env="production", publish_enabled=True, dry_run=False)

    def test_blocks_empty_content(self):
        report = pre_publish_check("", "test-001", self._safe_config())
        self.assertFalse(report.allowed)
        self.assertEqual(report.mode, "blocked")

    def test_blocks_test_content(self):
        report = pre_publish_check("123", "test-001", self._safe_config())
        self.assertFalse(report.allowed)

    def test_blocks_duplicate_content_id(self):
        report = pre_publish_check(
            "This is a valid real piece of content.",
            "already-published",
            self._safe_config(),
            published_content_ids=["already-published"],
        )
        self.assertFalse(report.allowed)

    def test_allows_dry_run_for_valid_content(self):
        report = pre_publish_check(
            "This is a valid real piece of content.",
            "fresh-content-001",
            self._safe_config(),
        )
        self.assertTrue(report.allowed)
        self.assertEqual(report.mode, "dry_run")
        self.assertTrue(report.is_dry_run)
        self.assertFalse(report.would_publish)

    def test_allows_production_for_valid_content(self):
        report = pre_publish_check(
            "This is a valid real piece of content.",
            "fresh-content-001",
            self._prod_config(),
        )
        self.assertTrue(report.allowed)
        self.assertEqual(report.mode, "production")
        self.assertTrue(report.would_publish)

    def test_blocks_production_when_daily_limit_hit(self):
        report = pre_publish_check(
            "This is a valid real piece of content.",
            "fresh-content-001",
            self._prod_config(),
            todays_post_count=10,
        )
        self.assertFalse(report.allowed)

    def test_blocks_production_when_circuit_breaker_tripped(self):
        report = pre_publish_check(
            "This is a valid real piece of content.",
            "fresh-content-001",
            self._prod_config(),
            consecutive_failures=5,
        )
        self.assertFalse(report.allowed)


if __name__ == "__main__":
    unittest.main()
