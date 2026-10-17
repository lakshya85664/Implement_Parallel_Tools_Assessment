
import time
from typing import Any


class FailingOrderProvider:
    """Provider test double that simulates an upstream failure."""

    def __init__(self, delay_seconds: float = 0):
        self.delay_seconds = delay_seconds
        self.calls = 0

    def get_order(
        self, order_id: str, customer_id: str
    ) -> dict[str, Any]:
        self.calls += 1
        if self.delay_seconds:
            time.sleep(self.delay_seconds)
        raise RuntimeError("Simulated upstream order provider failure")


class FailingShippingProvider:
    """Provider test double that simulates an upstream failure."""

    def __init__(self, delay_seconds: float = 0):
        self.delay_seconds = delay_seconds
        self.calls = 0

    def get_shipping_status(self, order_id: str) -> dict[str, Any]:
        self.calls += 1
        if self.delay_seconds:
            time.sleep(self.delay_seconds)
        raise RuntimeError("Simulated upstream shipping provider failure")
