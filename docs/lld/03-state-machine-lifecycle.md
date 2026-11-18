# Level 2: Low-Level Design (LLD) — State Machine & Request Lifecycle

**Document ID:** `DOC-LLD-03-STATE-MACHINE`  
**Project:** `automated-posting`  
**Author:** Principal Software Architect
**Reviewer:** Staff Backend Engineering Lead
**Status:** APPROVED  
**Standard:** UML 2.5 State Machine Specification

---

## 1. Request Processing State Machine

The overall lifecycle of an HTTP request traversing the system progresses through deterministic states:

```mermaid
stateDiagram-v2
    [*] --> RECEIVED: Client issues POST /posting
    
    RECEIVED --> VALIDATING: Parse Content-Type & Payload
    
    VALIDATING --> VALIDATION_FAILED: len > 200 OR URLs != 1
    VALIDATION_FAILED --> [*]: Emit HTTP 422 Unprocessable Entity
    
    VALIDATING --> VALIDATED: Invariants INV-001 & INV-002 Satisfied
    
    VALIDATED --> FANOUT_DISPATCH: Initialize PostingService & spawn 5 tasks
    
    state FANOUT_DISPATCH {
        [*] --> RUNNING: asyncio.gather initiated
        RUNNING --> AGGREGATING: All 5 platform coroutines settle
        AGGREGATING --> [*]
    }
    
    FANOUT_DISPATCH --> COMPILING_TELEMETRY: Compute counts (total, success, failed)
    
    COMPILING_TELEMETRY --> SERIALIZED: Convert to PostResponse model
    SERIALIZED --> [*]: Emit HTTP 200 OK
```

---

## 2. Platform Adapter Execution State Machine

Each platform adapter coroutine operates within an isolated, deterministic execution lifecycle:

```mermaid
stateDiagram-v2
    [*] --> INITIALIZING: Task scheduled by asyncio event loop
    
    INITIALIZING --> CONFIG_CHECK: Check is_configured()
    
    CONFIG_CHECK --> UNCONFIGURED: Missing Env Variables (.env)
    UNCONFIGURED --> FAILED_RESULT: Set error="Credentials not configured"
    
    CONFIG_CHECK --> EXECUTING: Credentials present
    
    state EXECUTING {
        [*] --> PREPARING_PAYLOAD: Adapt message/title
        PREPARING_PAYLOAD --> DISPATCHING_HTTP: httpx.post() outbound
        DISPATCHING_HTTP --> AWAITING_SOCKET: Non-blocking I/O
    }
    
    EXECUTING --> SUCCESS_RESULT: HTTP 200/201 & URL extracted
    EXECUTING --> TIMEOUT_RESULT: Execution exceeds 8.0s timeout
    EXECUTING --> RATE_LIMITED: HTTP 429 received
    EXECUTING --> AUTH_FAILED: HTTP 401/403 received
    EXECUTING --> HTTP_ERROR: HTTP 500/502/503 received
    
    TIMEOUT_RESULT --> FAILED_RESULT: error="Platform timeout after 8.0s"
    RATE_LIMITED --> FAILED_RESULT: error="Rate limit exceeded. Retry-After"
    AUTH_FAILED --> FAILED_RESULT: error="Authentication failed / token expired"
    HTTP_ERROR --> FAILED_RESULT: error="Upstream server error"
    
    SUCCESS_RESULT --> EMIT_PLATFORM_RESULT: status="success", public_access=True
    FAILED_RESULT --> EMIT_PLATFORM_RESULT: status="failed", public_access=False
    
    EMIT_PLATFORM_RESULT --> [*]: Return PlatformResult to gather()
```
