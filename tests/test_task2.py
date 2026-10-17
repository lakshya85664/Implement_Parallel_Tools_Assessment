
from adapters.fake_order_provider import FakeOrderProvider
from adapters.fake_shipping_provider import FakeShippingProvider
from parallel_tools_assessment import run_parallel_order_summary


def test_parallel_tool_combines_order_and_shipping():
    result = run_parallel_order_summary(
        {"order_id": "ORD-1001", "customer_id": "CUS-101"},
        {"subject": "support-agent-1", "role": "customer_support"},
    )

    assert result["status"] == "ok"
    assert result["data"]["execution_mode"] == "parallel"
    assert result["data"]["order"]["status"] == "confirmed"
    assert result["data"]["shipping"]["shipping_status"] == "in_transit"


def test_both_independent_providers_are_called():
    orders = FakeOrderProvider(delay_seconds=0)
    shipping = FakeShippingProvider(delay_seconds=0)

    result = run_parallel_order_summary(
        {"order_id": "ORD-1001", "customer_id": "CUS-101"},
        {"subject": "support-agent-1", "role": "customer_support"},
        order_provider=orders,
        shipping_provider=shipping,
    )

    assert result["status"] == "ok"
    assert len(orders.calls) == 1
    assert len(shipping.calls) == 1


def test_invalid_input_is_rejected_before_provider_calls():
    orders = FakeOrderProvider(delay_seconds=0)
    shipping = FakeShippingProvider(delay_seconds=0)

    result = run_parallel_order_summary(
        {"order_id": "ORD-1001"},
        {"subject": "support-agent-1", "role": "customer_support"},
        order_provider=orders,
        shipping_provider=shipping,
    )

    assert result["status"] == "invalid"
    assert orders.calls == []
    assert shipping.calls == []


def test_unauthorized_principal_is_denied_before_provider_calls():
    orders = FakeOrderProvider(delay_seconds=0)
    shipping = FakeShippingProvider(delay_seconds=0)

    result = run_parallel_order_summary(
        {"order_id": "ORD-1001", "customer_id": "CUS-101"},
        {"subject": "untrusted-user", "role": "guest"},
        order_provider=orders,
        shipping_provider=shipping,
    )

    assert result["status"] == "denied"
    assert orders.calls == []
    assert shipping.calls == []


def test_unknown_arguments_are_rejected():
    result = run_parallel_order_summary(
        {
            "order_id": "ORD-1001",
            "customer_id": "CUS-101",
            "force_admin": True,
        },
        {"subject": "support-agent-1", "role": "customer_support"},
    )

    assert result["status"] == "invalid"
