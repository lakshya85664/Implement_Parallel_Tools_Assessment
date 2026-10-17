
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr


class ParallelOrderInput(BaseModel):
    """Input for reading order and shipping information."""

    model_config = ConfigDict(extra="forbid", strict=True)

    order_id: StrictStr = Field(
        min_length=1,
        max_length=64,
        description="Unique order identifier",
    )
    customer_id: StrictStr = Field(
        min_length=1,
        max_length=64,
        description="Customer identifier used for authorization",
    )


class OrderDetails(BaseModel):
    """Validated order information returned by the order provider."""

    model_config = ConfigDict(extra="forbid", strict=True)

    order_id: StrictStr
    customer_id: StrictStr
    status: StrictStr
    total_amount: float = Field(ge=0)


class ShippingDetails(BaseModel):
    """Validated shipping information returned by the shipping provider."""

    model_config = ConfigDict(extra="forbid", strict=True)

    order_id: StrictStr
    shipping_status: StrictStr
    tracking_number: StrictStr | None = None


class ParallelOrderOutput(BaseModel):
    """Combined output returned after both independent reads finish."""

    model_config = ConfigDict(extra="forbid", strict=True)

    order: OrderDetails
    shipping: ShippingDetails
    execution_mode: Literal["parallel"] = "parallel"


class ToolContract(BaseModel):
    """Metadata describing a registered tool."""

    model_config = ConfigDict(extra="forbid", strict=True)

    name: StrictStr
    version: StrictStr
    description: StrictStr
    input_model: Any
    output_model: Any
    access: Literal["read", "write"]
    allowed_roles: list[StrictStr]
    timeout_seconds: float = Field(gt=0, le=30)
    retryable: bool = False
    idempotent: bool = True


def build_parallel_order_contract() -> ToolContract:
    """Create the contract for the parallel order-summary tool."""

    return ToolContract(
        name="parallel_order_summary",
        version="1.0.0",
        description=(
            "Fetch order details and shipping status independently, "
            "then combine the results."
        ),
        input_model=ParallelOrderInput,
        output_model=ParallelOrderOutput,
        access="read",
        allowed_roles=["customer_support", "admin"],
        timeout_seconds=5.0,
        retryable=True,
        idempotent=True,
    )
