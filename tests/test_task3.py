
from adapters.fake_order_provider import FakeOrderProvider
from adapters.fake_shipping_provider import FakeShippingProvider
from adapters.failure_injection import (
    FailingOrderProvider,
    FailingShippingProvider,
)
from parallel_tools_assessment import run_parallel_order_summary


def valid_arguments():
    return {
        "order_id": "ORD-1001",
        "customer_id": "CUS-101",
    }


def support_principal():
    return {
        "subject": "support-agent-1",
        "role": "customer_support",
    }


def test_malformed_input_never_calls_providers():
    order = FakeOrderProvider(delay_seconds=0)
    shipping = FakeShippingProvider(delay_seconds=0)

    result = run_parallel_order_summary(
        {"order_id": "ORD-1001", "customer_id": 123},
        support_principal(),
        order_provider=order,
        shipping_provider=shipping,
    )

    assert result["status"] == "invalid"
    assert order.calls == []
    assert shipping.calls == []


def test_guest_is_denied_without_provider_side_effects():
    order = FakeOrderProvider(delay_seconds=0)
    shipping = FakeShippingProvider(delay_seconds=0)

    result = run_parallel_order_summary(
        valid_arguments(),
        {"subject": "guest-1", "role": "guest"},
        order_provider=order,
        shipping_provider=shipping,
    )

    assert result["status"] == "denied"
    assert order.calls == []
    assert shipping.calls == []


def test_missing_subject_is_denied():
    result = run_parallel_order_summary(
        valid_arguments(),
        {"role": "admin"},
    )

    assert result["status"] == "denied"


def test_order_provider_failure_returns_safe_error():
    result = run_parallel_order_summary(
        valid_arguments(),
        support_principal(),
        order_provider=FailingOrderProvider(),
        shipping_provider=FakeShippingProvider(delay_seconds=0),
    )

    assert result["status"] == "provider_error"
    assert "Simulated upstream" not in str(result)
    assert any(
        event["event"] == "parallel.provider_error"
        for event in result["events"]
    )


def test_shipping_provider_failure_returns_safe_error():
    result = run_parallel_order_summary(
        valid_arguments(),
        support_principal(),
        order_provider=FakeOrderProvider(delay_seconds=0),
        shipping_provider=FailingShippingProvider(),
    )

    assert result["status"] == "provider_error"
    assert "Simulated upstream" not in str(result)


def test_timeout_returns_safe_status():
    result = run_parallel_order_summary(
        valid_arguments(),
        support_principal(),
        order_provider=FakeOrderProvider(delay_seconds=0.2),
        shipping_provider=FakeShippingProvider(delay_seconds=0.2),
        timeout_seconds=0.01,
    )

    assert result["status"] == "timeout"
    assert any(
        event["event"] == "parallel.timeout"
        for event in result["events"]
    )
