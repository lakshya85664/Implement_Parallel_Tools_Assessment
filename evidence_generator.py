
import json
import time
from pathlib import Path

from adapters.fake_order_provider import FakeOrderProvider
from adapters.fake_shipping_provider import FakeShippingProvider
from parallel_tools_assessment import run_parallel_order_summary
from reliability.controls import ReliabilityController


ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"
TRACES = ROOT / "traces"
REPORTS = ROOT / "reports"

for directory in (OUTPUTS, TRACES, REPORTS):
    directory.mkdir(parents=True, exist_ok=True)


def main():
    principal = {
        "subject": "evidence-agent",
        "role": "customer_support",
    }
    arguments = {
        "order_id": "ORD-EVIDENCE-001",
        "customer_id": "CUS-EVIDENCE-001",
    }

    controller = ReliabilityController()
    order_provider = FakeOrderProvider(delay_seconds=0.05)
    shipping_provider = FakeShippingProvider(delay_seconds=0.05)

    started = time.perf_counter()
    first = run_parallel_order_summary(
        arguments,
        principal,
        order_provider=order_provider,
        shipping_provider=shipping_provider,
        reliability=controller,
        idempotency_key="evidence-request-001",
    )
    elapsed = time.perf_counter() - started

    second = run_parallel_order_summary(
        arguments,
        principal,
        order_provider=order_provider,
        shipping_provider=shipping_provider,
        reliability=controller,
        idempotency_key="evidence-request-001",
    )

    trace = {
        "task": "parallel_tool_execution",
        "first_response": first,
        "second_response": second,
        "elapsed_seconds": round(elapsed, 6),
        "provider_call_counts": {
            "order": len(order_provider.calls),
            "shipping": len(shipping_provider.calls),
        },
        "metrics": controller.metrics.snapshot(),
    }

    (TRACES / "parallel_execution_trace.json").write_text(
        json.dumps(trace, indent=2),
        encoding="utf-8",
    )

    summary = {
        "status": "completed" if (
            first.get("status") == "ok"
            and second.get("status") == "ok"
            and len(order_provider.calls) == 1
            and len(shipping_provider.calls) == 1
        ) else "check_required",
        "first_call_status": first.get("status"),
        "second_call_status": second.get("status"),
        "idempotency_cache_hit": any(
            event.get("event") == "idempotency.cache_hit"
            for event in second.get("events", [])
        ),
        "elapsed_seconds": round(elapsed, 6),
        "provider_call_counts": {
            "order": len(order_provider.calls),
            "shipping": len(shipping_provider.calls),
        },
        "metrics": controller.metrics.snapshot(),
    }

    (OUTPUTS / "evidence_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    report = f"""# Parallel Tools Operator Report

## Execution summary

- Overall status: {summary["status"]}
- First request: {summary["first_call_status"]}
- Repeated request: {summary["second_call_status"]}
- Idempotency cache hit: {summary["idempotency_cache_hit"]}
- Initial execution duration: {summary["elapsed_seconds"]} seconds

## Provider call counts

- Order provider: {summary["provider_call_counts"]["order"]}
- Shipping provider: {summary["provider_call_counts"]["shipping"]}

## Metrics

```json
{json.dumps(summary["metrics"], indent=2)}
```

## Evidence files

- `outputs/evidence_summary.json`
- `traces/parallel_execution_trace.json`

## Limitations

This demonstration uses deterministic fake providers and an in-memory
reliability controller. It does not establish production performance,
distributed idempotency, or external-service reliability.
"""

    (REPORTS / "operator_report.md").write_text(
        report,
        encoding="utf-8",
    )

    print("Evidence generation complete.")
    print(json.dumps(summary, indent=2))
    print(f"Trace: {TRACES / 'parallel_execution_trace.json'}")
    print(f"Summary: {OUTPUTS / 'evidence_summary.json'}")
    print(f"Report: {REPORTS / 'operator_report.md'}")


if __name__ == "__main__":
    main()
