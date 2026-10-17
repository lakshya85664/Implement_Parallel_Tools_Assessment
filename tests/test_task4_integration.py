
from adapters.fake_order_provider import FakeOrderProvider
from adapters.fake_shipping_provider import FakeShippingProvider
from parallel_tools_assessment import run_parallel_order_summary
from reliability.controls import ReliabilityController


def arguments():
    return {"order_id": "ORD-2001", "customer_id": "CUS-201"}


def principal():
    return {"subject": "agent-integration", "role": "customer_support"}


def test_repeated_request_uses_idempotency_cache():
    controller = ReliabilityController()
    order = FakeOrderProvider(delay_seconds=0)
    shipping = FakeShippingProvider(delay_seconds=0)

    first = run_parallel_order_summary(
        arguments(), principal(), order, shipping,
        reliability=controller, idempotency_key="same-request",
    )
    second = run_parallel_order_summary(
        arguments(), principal(), order, shipping,
        reliability=controller, idempotency_key="same-request",
    )

    assert first["status"] == "ok"
    assert second["status"] == "ok"
    assert any(
        event["event"] == "idempotency.cache_hit"
        for event in second["events"]
    )
    assert len(order.calls) == 1
    assert len(shipping.calls) == 1


def test_rate_limit_is_enforced_by_gateway():
    controller = ReliabilityController(rate_limit=1, window_seconds=60)

    first = run_parallel_order_summary(
        arguments(), principal(),
        FakeOrderProvider(delay_seconds=0),
        FakeShippingProvider(delay_seconds=0),
        reliability=controller,
        idempotency_key="request-one",
    )

    second = run_parallel_order_summary(
        {"order_id": "ORD-2002", "customer_id": "CUS-202"},
        principal(),
        FakeOrderProvider(delay_seconds=0),
        FakeShippingProvider(delay_seconds=0),
        reliability=controller,
        idempotency_key="request-two",
    )

    assert first["status"] == "ok"
    assert second["status"] == "rate_limited"
    assert controller.metrics.snapshot()["rate_limited"] == 1


def test_metrics_track_success_and_cache_hit():
    controller = ReliabilityController()
    args = arguments()
    user = principal()

    run_parallel_order_summary(
        args, user,
        FakeOrderProvider(delay_seconds=0),
        FakeShippingProvider(delay_seconds=0),
        reliability=controller,
    )
    run_parallel_order_summary(
        args, user,
        FakeOrderProvider(delay_seconds=0),
        FakeShippingProvider(delay_seconds=0),
        reliability=controller,
    )

    metrics = controller.metrics.snapshot()
    assert metrics["started"] == 1
    assert metrics["succeeded"] == 1


def test_provider_failure_is_counted():
    class BrokenOrder:
        def get_order(self, order_id, customer_id):
            raise ValueError("private provider details")

    controller = ReliabilityController(max_attempts=2)

    result = run_parallel_order_summary(
        arguments(),
        principal(),
        BrokenOrder(),
        FakeShippingProvider(delay_seconds=0),
        reliability=controller,
        idempotency_key="broken-order",
    )

    assert result["status"] == "provider_error"
    assert "private provider details" not in str(result)
    metrics = controller.metrics.snapshot()
    assert metrics["failed"] == 1
    assert metrics["retries"] == 1
