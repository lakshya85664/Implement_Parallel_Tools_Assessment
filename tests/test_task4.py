
import threading
import time

import pytest

from reliability.controls import (
    ExecutionMetrics,
    IdempotencyStore,
    RetryPolicy,
    SlidingWindowRateLimiter,
)
from adapters.fake_order_provider import FakeOrderProvider
from adapters.fake_shipping_provider import FakeShippingProvider
from parallel_tools_assessment import run_parallel_order_summary


def test_retry_policy_recovers_after_transient_failure():
    policy = RetryPolicy(max_attempts=3)
    attempts = {"count": 0}

    def operation():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ValueError("temporary failure")
        return "success"

    assert policy.run(operation) == "success"
    assert attempts["count"] == 3


def test_retry_policy_stops_after_max_attempts():
    policy = RetryPolicy(max_attempts=2)
    attempts = {"count": 0}

    def operation():
        attempts["count"] += 1
        raise ValueError("failure")

    with pytest.raises(RuntimeError):
        policy.run(operation)

    assert attempts["count"] == 2


def test_retry_policy_rejects_unsafe_attempt_count():
    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=10)


def test_sliding_window_rate_limiter():
    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=1)

    assert limiter.allow()
    assert limiter.allow()
    assert not limiter.allow()


def test_idempotency_store_reuses_completed_result():
    store = IdempotencyStore()
    store.put("request-1", {"status": "ok"})

    assert store.get("request-1") == {"status": "ok"}
    assert store.get("missing") is None


def test_metrics_are_thread_safe():
    metrics = ExecutionMetrics()

    threads = [
        threading.Thread(target=metrics.increment, args=("started",))
        for _ in range(100)
    ]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert metrics.snapshot()["started"] == 100


def test_parallel_calls_overlap_in_time():
    delay = 0.15
    order = FakeOrderProvider(delay_seconds=delay)
    shipping = FakeShippingProvider(delay_seconds=delay)

    started = time.monotonic()

    result = run_parallel_order_summary(
        {"order_id": "ORD-1001", "customer_id": "CUS-101"},
        {"subject": "support-agent-1", "role": "customer_support"},
        order_provider=order,
        shipping_provider=shipping,
    )

    elapsed = time.monotonic() - started

    assert result["status"] == "ok"
    # Sequential execution would take about 0.30 seconds.
    # Allow margin for slower CI machines while requiring overlap.
    assert elapsed < 0.27
