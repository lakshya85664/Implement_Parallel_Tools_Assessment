
import time
from typing import Any


class FakeOrderProvider:
    """Deterministic order provider for development and testing."""

    def __init__(self, delay_seconds: float = 0.05):
        self.delay_seconds = delay_seconds
        self.calls: list[dict[str, Any]] = []

    def get_order(self, order_id: str, customer_id: str) -> dict[str, Any]:
        self.calls.append({
            "order_id": order_id,
            "customer_id": customer_id,
        })
        time.sleep(self.delay_seconds)

        return {
            "order_id": order_id,
            "customer_id": customer_id,
            "status": "confirmed",
            "total_amount": 1499.0,
        }
