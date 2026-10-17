
from collections import deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Any, Callable


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded retry policy for provider operations."""

    max_attempts: int = 3

    def __post_init__(self):
        if not 1 <= self.max_attempts <= 5:
            raise ValueError("max_attempts must be between 1 and 5")

    def run(self, operation: Callable[[], Any]) -> Any:
        """Run an operation with bounded retries.

        Timeout exceptions are propagated immediately so the gateway
        can return a timeout response instead of retrying them.
        """
        last_error = None

        for _ in range(self.max_attempts):
            try:
                return operation()
            except TimeoutError:
                raise
            except Exception as exc:
                last_error = exc

        raise RuntimeError(
            "Operation failed after retry attempts"
        ) from last_error


class SlidingWindowRateLimiter:
    """Thread-safe sliding-window request limiter."""

    def __init__(self, limit: int, window_seconds: float):
        if limit < 1 or window_seconds <= 0:
            raise ValueError("Invalid rate-limit configuration")

        self.limit = limit
        self.window_seconds = window_seconds
        self._calls = deque()
        self._lock = Lock()

    def allow(self) -> bool:
        """Return True and record a call if capacity is available."""
        now = monotonic()

        with self._lock:
            while (
                self._calls
                and now - self._calls[0] >= self.window_seconds
            ):
                self._calls.popleft()

            if len(self._calls) >= self.limit:
                return False

            self._calls.append(now)
            return True


class IdempotencyStore:
    """Thread-safe in-memory store for completed operation results."""

    def __init__(self):
        self._results: dict[str, Any] = {}
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            return self._results.get(key)

    def put(self, key: str, result: Any) -> None:
        with self._lock:
            self._results[key] = result


class ExecutionMetrics:
    """Thread-safe execution counters."""

    def __init__(self):
        self._counts = {
            "started": 0,
            "succeeded": 0,
            "failed": 0,
            "retries": 0,
            "rate_limited": 0,
        }
        self._lock = Lock()

    def increment(self, name: str) -> None:
        with self._lock:
            if name not in self._counts:
                raise ValueError(f"Unknown metric: {name}")
            self._counts[name] += 1

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counts)


class ReliabilityController:
    """Coordinate rate limiting, idempotency, retries, and metrics."""

    def __init__(
        self,
        rate_limit: int = 10,
        window_seconds: float = 60.0,
        max_attempts: int = 3,
    ):
        self.retry_policy = RetryPolicy(max_attempts=max_attempts)
        self.rate_limiter = SlidingWindowRateLimiter(
            limit=rate_limit,
            window_seconds=window_seconds,
        )
        self.idempotency_store = IdempotencyStore()
        self.metrics = ExecutionMetrics()
        self._execution_lock = Lock()

    def execute(
        self,
        key: str,
        operation: Callable[[], Any],
    ) -> tuple[Any, bool]:
        """Execute an operation once per key and cache its success.

        Returns:
            A tuple containing (result, cache_hit).
        """
        with self._execution_lock:
            cached = self.idempotency_store.get(key)
            if cached is not None:
                return cached, True

            if not self.rate_limiter.allow():
                self.metrics.increment("rate_limited")
                raise RuntimeError("Rate limit exceeded")

            self.metrics.increment("started")
            attempts = 0

            def counted_operation():
                nonlocal attempts
                attempts += 1

                if attempts > 1:
                    self.metrics.increment("retries")

                return operation()

            try:
                result = self.retry_policy.run(counted_operation)
                self.idempotency_store.put(key, result)
                self.metrics.increment("succeeded")
                return result, False

            except Exception:
                self.metrics.increment("failed")
                raise
