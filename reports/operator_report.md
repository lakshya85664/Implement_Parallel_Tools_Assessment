# Parallel Tools Operator Report

## Execution summary

- Overall status: completed
- First request: ok
- Repeated request: ok
- Idempotency cache hit: True
- Initial execution duration: 0.053915 seconds

## Provider call counts

- Order provider: 1
- Shipping provider: 1

## Metrics

```json
{
  "started": 1,
  "succeeded": 1,
  "failed": 0,
  "retries": 0,
  "rate_limited": 0
}
```

## Evidence files

- `outputs/evidence_summary.json`
- `traces/parallel_execution_trace.json`

## Limitations

This demonstration uses deterministic fake providers and an in-memory
reliability controller. It does not establish production performance,
distributed idempotency, or external-service reliability.
