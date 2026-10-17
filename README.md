# Implement Parallel Tools Assessment

## Overview
This project demonstrates a parallel tool-execution gateway that retrieves order details and shipping status concurrently, validates the combined result, and applies basic access and reliability controls.

## Learning objectives
- Define typed input/output contracts with Pydantic.
- Register tool metadata, access mode, allowed roles, timeout, retry, and idempotency properties.
- Fan out independent provider calls using a bounded worker pool and combine their results.
- Validate inputs before provider calls and reject unauthorized principals.
- Return safe errors for provider failures and timeouts.
- Implement bounded retries, sliding-window rate limiting, idempotency caching, and thread-safe execution metrics.
- Generate evidence traces and an operator report.

## Project structure
```text
Implement_Parallel_Tools_Assessment/
├── adapters/
├── reliability/controls.py
├── schemas/
├── tests/
├── outputs/evidence_summary.json
├── traces/parallel_execution_trace.json
├── reports/operator_report.md
├── parallel_tools_assessment.py
├── evidence_generator.py
├── requirements.txt
└── .gitignore
```

## Requirements
- Python 3.13.x
- Pydantic 2.14.1
- Pytest 9.1.1
- HTTPX 0.28.1

Install dependencies:
```cmd
python -m pip install -r requirements.txt
```

## Run the demonstration
```cmd
python parallel_tools_assessment.py
```
A successful run returns `status: ok`, a validated order and shipping payload, and `execution_mode: parallel`.

## Run tests
```cmd
python -m pytest -q
```
Latest recorded result: `30 passed`.

The task test files cover contract and registry validation, parallel provider calls, invalid input, authorization, provider failures, timeout behavior, retry policy, rate limiting, idempotency, metrics, and integration behavior.

## Generate evidence
```cmd
python evidence_generator.py
type outputs\evidence_summary.json
type reports\operator_report.md
```
Generated artifacts:
- `outputs/evidence_summary.json`
- `traces/parallel_execution_trace.json`
- `reports/operator_report.md`

The latest evidence run reported `completed`, one call to each provider, an idempotency cache hit on the repeated request, and 0.053915 seconds for the initial fake-provider execution.

## Architecture
1. **Contract layer:** Pydantic models reject missing, malformed, and unexpected input fields and validate the combined output.
2. **Authorization:** The gateway checks the caller's role and subject before invoking providers.
3. **Parallel execution:** Order and shipping reads are submitted independently to a two-worker thread pool, then their results are combined.
4. **Reliability controls:** The reliability module provides bounded retries, a thread-safe sliding-window limiter, an in-memory idempotency store, and execution counters.
5. **Observability:** The gateway emits structured event names; the evidence generator persists a summary, trace, and operator report.

## Limitations and production considerations
- Fake providers are deterministic test doubles; they do not demonstrate real upstream reliability.
- The idempotency store and rate limiter are in-memory and process-local. Multi-process or distributed deployment requires shared storage and coordinated limits.
- Cancelling a Python future cannot forcibly stop a running thread. Real HTTP adapters must enforce network-level connection/read timeouts.
- Retry classification should distinguish transient failures from permanent failures.
- The timing figure is a local demonstration measurement, not a general performance guarantee.
- HTTPX is included for future real HTTP adapters; the current evidence run uses fake providers.

## Reflection (approximately 300 words)
This assessment helped me connect tool definitions with the operational concerns that arise when an agent invokes more than one tool. A tool contract is not only a function signature: it also describes expected input and output, access mode, allowed roles, timeout, and reliability expectations. Pydantic validation provides a clear boundary that prevents malformed or unexpected arguments from reaching provider code.

The most important implementation concept was fan-out/fan-in. Order details and shipping status are independent reads, so submitting both to a bounded worker pool allows them to overlap. The gateway then validates and combines their results into one response. Tests for provider call counts and elapsed time help distinguish concurrent execution from a sequential implementation, although timing measurements should always be interpreted in the context of the local test environment.

The failure tests also showed why safe error handling matters. Callers should receive stable status values and useful event names without exposing internal exception messages. Authorization checks must happen before provider calls, and invalid inputs should not cause external side effects. Reliability features such as bounded retries, rate limiting, idempotency, and metrics are most useful when integrated into the actual execution path and verified with end-to-end tests rather than tested only as isolated utilities.

A debugging lesson was that a globally shared idempotency cache can contaminate independent tests when the cache key does not reflect the full execution context. Making the controller explicit and isolating default instances helped preserve expected behavior while still allowing intentional cache reuse when a controller is shared.

The project is a learning implementation, not a production service. The current providers are fakes, and in-memory controls do not coordinate across processes. Before production use, I would add real HTTP adapters with network-level timeouts, a durable shared idempotency store, more selective retry rules, stronger concurrency tests, and monitoring tied to operational requirements. Overall, the assessment improved my understanding of how to combine typed contracts, parallelism, security, reliability, and evidence-driven testing into a small tool gateway.
