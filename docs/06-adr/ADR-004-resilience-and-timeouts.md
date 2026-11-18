# ADR-004: Resiliency, Timeout Governance & Bulkhead Isolation

**Status:** ACCEPTED  
**Date:** 2026-11-18  
**Author:** Principal Solutions Architect
**Reviewer:** Technical Architecture Review Board
**Governed Issue:** ISSUE-005 (Timeout Cascading Failure)  

---

## 1. Context & Problem Statement
External third-party platform APIs exhibit unpredictable latency, transient outages, network packet drops, and sudden connection freezes. If one platform's API server stalls indefinitely, a naive fan-out implementation will cause the entire `POST /posting` endpoint to hang until the client or gateway times out, violating our $\le 10\text{s}$ SLA.

## 2. Decision Drivers
- Strict SLA preservation ($\le 10\text{s}$ total turnaround).
- Bulkhead fault containment (one slow/dead API must not drag down the whole service).
- Granular diagnostic error attribution per platform.
- Clean resource cleanup (cancelling stalled coroutines to avoid socket leaks).

## 3. Considered Options
1. **Dual-Tier Timeout (Global 10.0s + Per-Adapter 8.0s via `asyncio.wait_for`)**
2. **Single Global Timeout Only (FastAPI Middleware)**
3. **No Timeout (Rely on HTTP Client Default Socket Timeouts)**

## 4. Decision Outcome
**Chosen Option:** **Dual-Tier Timeout Architecture**

### Architectural Blueprint:
```
[ Ingress Request ] ──────────────────────────────────────────┐ (Global Timeout: 10.0s)
  │                                                           │
  ├──► LinkedIn Adapter ───► asyncio.wait_for(..., timeout=8.0s)──► Result
  ├──► Dev.to Adapter   ───► asyncio.wait_for(..., timeout=8.0s)──► Result
  ├──► Hashnode Adapter ───► asyncio.wait_for(..., timeout=8.0s)──► Result
  ├──► Mastodon Adapter ───► asyncio.wait_for(..., timeout=8.0s)──► Result
  └──► Telegram Adapter ───► asyncio.wait_for(..., timeout=8.0s)──► Result
```

### Positive Consequences:
- **Fast Failure for Stalled Adapters:** If LinkedIn hangs, after exactly 8.0 seconds `asyncio.wait_for` cancels the coroutine, catches `asyncio.TimeoutError`, and converts it into `status: "failed", error: "Platform timeout after 8s"`.
- **Buffer for Aggregation:** The 2.0-second delta between adapter timeout (8.0s) and global SLA (10.0s) ensures the system has ample time to aggregate results, format the JSON envelope, and transmit it to the client before the gateway times out.
- **Bulkhead Guarantee:** The remaining 4 platforms complete independently and deliver successful results.

---

## 5. Pros and Cons of Alternatives

### Single Global Timeout Only
- *Pros:* Simpler to configure in middleware.
- *Cons:* If one platform hangs, the entire request is aborted at 10.0s, returning HTTP 504 Gateway Timeout to the client without returning the results of the 4 platforms that succeeded.

### No Timeout / Socket Default Only
- *Pros:* Minimum code.
- *Cons:* Python's default socket timeout can be 60+ seconds or indefinite on TCP freeze, completely locking server resources and failing the test evaluation.
