# ADR-003: Concurrency Engine & Fan-Out Strategy (asyncio.gather vs ThreadPool vs Celery)

**Status:** ACCEPTED  
**Date:** 2026-11-18  
**Author:** Principal Solutions Architect
**Reviewer:** Technical Architecture Review Board
**Governed Issue:** ISSUE-004, ISSUE-013  

---

## 1. Context & Problem Statement
When a single request arrives at `POST /posting`, the system must publish the payload across 5 independent platforms simultaneously. We need to decide how to schedule and execute these 5 tasks concurrently, aggregate their results, and return the response within the 10.0-second SLA.

## 2. Decision Drivers
- Minimal latency (total time = max adapter latency, not sum).
- Zero external infrastructure dependency (avoid message brokers if not required for simple fan-out).
- Memory efficiency and low CPU overhead.
- Exception isolation: failure in one task must not abort others.
- Thread-safety and prevention of race conditions.

## 3. Considered Options
1. **`asyncio.gather(..., return_exceptions=True)`**
2. **`concurrent.futures.ThreadPoolExecutor`**
3. **Distributed Task Queue (Celery / RabbitMQ / Redis)**

## 4. Decision Outcome
**Chosen Option:** **`asyncio.gather(..., return_exceptions=True)`**

### Positive Consequences:
- **Zero OS Thread Overhead:** All 5 requests run on the single Python process event loop as lightweight coroutines ($\sim 1\text{KB}$ memory each vs $\sim 8\text{MB}$ stack per OS thread).
- **Graceful Failure Aggregation:** With `return_exceptions=True`, if one coroutine raises an unhandled exception, `asyncio.gather` catches it, stores the exception instance in the results list, and continues waiting for the remaining coroutines.
- **Synchronous Response Delivery:** The client receives the complete breakdown of all 5 platform results in the immediate HTTP response body without needing complex polling or webhook infrastructure.

### Negative Consequences:
- Unhandled CPU-bound operations could delay I/O scheduling (not applicable here, as all adapter tasks are pure I/O).

---

## 5. Pros and Cons of Alternatives

### ThreadPoolExecutor
- *Pros:* Works with synchronous code.
- *Cons:* Heavy resource overhead (thread context switching); subject to Python's Global Interpreter Lock (GIL); race conditions possible if shared state is accessed; more complex exception propagation.

### Celery with RabbitMQ/Redis
- *Pros:* Durable message persistence, background retries over days.
- *Cons:* Complete overkill for an interactive REST API test with a single endpoint; requires running and managing multiple separate processes/servers (broker, worker, backend); prevents returning an immediate synchronous response to `POST /posting`.
