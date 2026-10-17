
import time
from typing import Any


class FakeShippingProvider:
    """Deterministic shipping provider for development and testing."""

    def __init__(self, delay_seconds: float = 0.05):
        self.delay_seconds = delay_seconds
        self.calls: list[dict[str, Any]] = []

    def get_shipping_status(self, order_id: str) -> dict[str, Any]:
        self.calls.append({"order_id": order_id})
        time.sleep(self.delay_seconds)

        return {
            "order_id": order_id,
            "shipping_status": "in_transit",
            "tracking_number": f"TRACK-{order_id}",
        }
