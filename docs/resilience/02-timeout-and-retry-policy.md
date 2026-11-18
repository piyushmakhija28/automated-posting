# Level 4: Reliability & Fault Tolerance Architecture — Timeout & Retry Policy

**Document ID:** `DOC-RES-02-TIMEOUTS`  
**Project:** `automated-posting`  
**Author:** Principal Software Architect
**Reviewer:** Staff Backend Engineering Lead
**Status:** APPROVED  
**Standard:** Resilience4j & AWS Architecture Center Exponential Backoff Standards

---

## 1. Dual-Tier Timeout Specification

To guarantee that the API satisfies its strict $\le 10.0$-second SLA under all network conditions, the engine enforces a **Dual-Tier Timeout Architecture**:

| Tier | Boundary | Duration | Enforcement Primitive | Action Upon Breach |
|---|---|---|---|---|
| **Level 1 (Adapter SLA)** | Individual Platform Adapter | **8.0 Seconds** | `asyncio.wait_for(coro, timeout=8.0)` | Coroutine cancelled; socket closed; returns `status: "failed", error: "Platform timeout after 8.0s"`. |
| **Level 2 (Gateway SLA)** | Whole HTTP Request Lifecycle | **10.0 Seconds** | Uvicorn / Reverse Proxy SLA Boundary | Safety buffer guaranteeing server emits JSON telemetry before reverse proxy disconnects. |

### Why 8.0s vs 10.0s?
The $2.0$-second delta provides the necessary execution headroom for:
- Task cancellation cleanup.
- Local list aggregation and count computation.
- JSON serialization and response stream flushing.

---

## 2. Exponential Backoff with Full Jitter Strategy

For transient network errors (e.g. HTTP 503 Service Unavailable or TCP connection resets), standard immediate retries can overwhelm an already struggling upstream platform (the "thundering herd" problem).

Where internal retries are enabled, the system applies **Full Jitter Exponential Backoff**:

$$t_{\text{sleep}} = \text{random_between}\Big(0, \min(T_{\text{max}}, T_{\text{base}} \times 2^{\text{attempt}})\Big)$$

where:
- $T_{\text{base}} = 0.5\text{ seconds}$
- $T_{\text{max}} = 2.0\text{ seconds}$
- $\text{max\_attempts} = 2$ (capped to stay within the 8.0-second total adapter budget).

```python
import asyncio
import random

async def retry_with_jitter(coro_fn, max_attempts=2, base_delay=0.5, max_delay=2.0):
    for attempt in range(max_attempts):
        try:
            return await coro_fn()
        except (httpx.ConnectError, httpx.ReadTimeout) as exc:
            if attempt == max_attempts - 1:
                raise exc
            delay = random.uniform(0, min(max_delay, base_delay * (2 ** attempt)))
            await asyncio.sleep(delay)
```
