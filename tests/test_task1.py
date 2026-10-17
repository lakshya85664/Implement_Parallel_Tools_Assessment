
import pytest
from pydantic import ValidationError

from schemas.registry import build_registry, get_tool
from schemas.tool_contract import (
    ParallelOrderInput,
    ParallelOrderOutput,
)


def test_registry_contains_parallel_order_tool():
    registry = build_registry()

    assert "parallel_order_summary" in registry
    assert registry["parallel_order_summary"].version == "1.0.0"


def test_tool_is_read_only_and_has_role_policy():
    tool = get_tool("parallel_order_summary")

    assert tool is not None
    assert tool.access == "read"
    assert "customer_support" in tool.allowed_roles
    assert "admin" in tool.allowed_roles
    assert tool.timeout_seconds > 0


def test_valid_input_is_accepted():
    data = ParallelOrderInput(
        order_id="ORD-1001",
        customer_id="CUS-101",
    )

    assert data.order_id == "ORD-1001"
    assert data.customer_id == "CUS-101"


def test_missing_customer_id_is_rejected():
    with pytest.raises(ValidationError):
        ParallelOrderInput(order_id="ORD-1001")


def test_unknown_input_field_is_rejected():
    with pytest.raises(ValidationError):
        ParallelOrderInput(
            order_id="ORD-1001",
            customer_id="CUS-101",
            admin_override=True,
        )


def test_wrong_input_type_is_rejected():
    with pytest.raises(ValidationError):
        ParallelOrderInput(
            order_id=1001,
            customer_id="CUS-101",
        )


def test_output_contract_accepts_combined_result():
    result = ParallelOrderOutput(
        order={
            "order_id": "ORD-1001",
            "customer_id": "CUS-101",
            "status": "confirmed",
            "total_amount": 1499.0,
        },
        shipping={
            "order_id": "ORD-1001",
            "shipping_status": "in_transit",
            "tracking_number": "TRACK-1001",
        },
    )

    assert result.execution_mode == "parallel"
    assert result.shipping.shipping_status == "in_transit"


def test_unknown_tool_returns_none():
    assert get_tool("unknown_tool") is None
