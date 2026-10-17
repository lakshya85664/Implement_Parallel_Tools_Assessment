
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from hashlib import sha256
from threading import Lock
from typing import Any
import json
import time

from pydantic import ValidationError

from adapters.fake_order_provider import FakeOrderProvider
from adapters.fake_shipping_provider import FakeShippingProvider
from reliability.controls import ReliabilityController
from schemas.tool_contract import (
    ParallelOrderInput,
    ParallelOrderOutput,
)



_DEFAULT_KEY_LOCK = Lock()
_IN_FLIGHT_KEYS: set[str] = set()


def run_parallel_order_summary(
    arguments: dict[str, Any],
    principal: dict[str, Any],
    order_provider: FakeOrderProvider | None = None,
    shipping_provider: FakeShippingProvider | None = None,
    timeout_seconds: float = 5.0,
    reliability: ReliabilityController | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Validate, authorize, execute parallel reads, and combine results."""

    events: list[dict[str, Any]] = []

    try:
        request = ParallelOrderInput.model_validate(arguments)
    except ValidationError as exc:
        return {
            "status": "invalid",
            "error": "Invalid tool arguments",
            "details": exc.errors(include_input=False),
            "events": events,
        }

    role = principal.get("role")
    subject = principal.get("subject")

    if role not in {"customer_support", "admin"} or not subject:
        events.append({"event": "authorization.denied"})
        return {
            "status": "denied",
            "error": "Authorization denied",
            "events": events,
        }

    order_provider = order_provider or FakeOrderProvider()
    shipping_provider = shipping_provider or FakeShippingProvider()
    # Isolate independent calls by default. Pass an explicit shared
    # controller when cache and rate-limit state should persist.
    if reliability is None:
        reliability = ReliabilityController()

    # Bind the key to caller identity and request content.
    request_payload = json.dumps(
        request.model_dump(), sort_keys=True, separators=(",", ":")
    )
    digest = sha256(request_payload.encode()).hexdigest()
    raw_key = idempotency_key or digest
    key = f"{subject}:{raw_key}:{digest}"

    with _DEFAULT_KEY_LOCK:
        if key in _IN_FLIGHT_KEYS:
            return {
                "status": "conflict",
                "error": "An identical request is already in progress",
                "events": [{"event": "idempotency.in_flight"}],
            }
        _IN_FLIGHT_KEYS.add(key)

    events.append({
        "event": "parallel.started",
        "tool": "parallel_order_summary",
        "subject": subject,
    })

    def invoke_providers():
        executor = ThreadPoolExecutor(max_workers=2)
        started = time.monotonic()

        order_future = executor.submit(
            order_provider.get_order,
            request.order_id,
            request.customer_id,
        )
        shipping_future = executor.submit(
            shipping_provider.get_shipping_status,
            request.order_id,
        )

        try:
            deadline = started + timeout_seconds
            order = order_future.result(
                timeout=max(0.0, deadline - time.monotonic())
            )
            shipping = shipping_future.result(
                timeout=max(0.0, deadline - time.monotonic())
            )

            result = ParallelOrderOutput.model_validate({
                "order": order,
                "shipping": shipping,
                "execution_mode": "parallel",
            })
            return result.model_dump()
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    try:
        data, cache_hit = reliability.execute(key, invoke_providers)

        if cache_hit:
            events.append({"event": "idempotency.cache_hit"})
        else:
            events.append({"event": "parallel.completed"})

        return {
            "status": "ok",
            "data": data,
            "events": events,
        }

    except RuntimeError as exc:
        if str(exc) == "Rate limit exceeded":
            events.append({"event": "rate_limit.rejected"})
            return {
                "status": "rate_limited",
                "error": "Rate limit exceeded",
                "events": events,
            }

        events.append({"event": "parallel.provider_error"})
        return {
            "status": "provider_error",
            "error": "Provider operation failed",
            "events": events,
        }

    except TimeoutError:
        events.append({"event": "parallel.timeout"})
        return {
            "status": "timeout",
            "error": "A provider exceeded the allowed wait time",
            "events": events,
        }

    except Exception:
        events.append({"event": "parallel.provider_error"})
        return {
            "status": "provider_error",
            "error": "A provider request failed",
            "events": events,
        }

    finally:
        with _DEFAULT_KEY_LOCK:
            _IN_FLIGHT_KEYS.discard(key)


if __name__ == "__main__":
    response = run_parallel_order_summary(
        arguments={
            "order_id": "ORD-1001",
            "customer_id": "CUS-101",
        },
        principal={
            "subject": "support-agent-1",
            "role": "customer_support",
        },
    )
    print(json.dumps(response, indent=2))
