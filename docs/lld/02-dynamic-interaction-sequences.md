# Level 2: Low-Level Design (LLD) — Dynamic Interaction Sequences

**Document ID:** `DOC-LLD-02-SEQUENCES`  
**Project:** `automated-posting`  
**Author:** Principal Software Architect
**Reviewer:** Staff Backend Engineering Lead
**Status:** APPROVED  
**Standard:** UML 2.5 Sequence Specification

---

## 1. Sequence 1: Happy Path Concurrent Fan-Out

In the standard operational scenario, a client issues a valid JSON payload. The router extracts the CTA link, delegates execution to `PostingService`, which spawns 5 parallel coroutines via `asyncio.gather`. All 5 adapters return `status: "success"`.

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant Router as app/main.py (POST /posting)
    participant Validator as app/utils/validators.py
    participant Service as app/services/posting_service.py
    participant LinkedIn as LinkedInPlatform
    participant DevTo as DevToPlatform
    participant Hashnode as HashnodePlatform
    participant Mastodon as MastodonPlatform
    participant Telegram as TelegramPlatform

    Client->>Router: POST /posting { "message": "..." }
    Router->>Validator: Validate message <= 200 & exactly 1 URL
    Validator-->>Router: Validation Passed (Extracted CTA URL)
    Router->>Service: post_to_all(message, cta_url)

    par Concurrently to 5 Platforms
        Service->>LinkedIn: post(message, cta_url) [timeout=8s]
        LinkedIn->>LinkedIn: POST /v2/ugcPosts (OAuth 2.0)
        LinkedIn-->>Service: PlatformResult(success, url_1)
    and
        Service->>DevTo: post(message, cta_url) [timeout=8s]
        DevTo->>DevTo: POST /api/articles (api-key)
        DevTo-->>Service: PlatformResult(success, url_2)
    and
        Service->>Hashnode: post(message, cta_url) [timeout=8s]
        Hashnode->>Hashnode: POST / (GraphQL mutation)
        Hashnode-->>Service: PlatformResult(success, url_3)
    and
        Service->>Mastodon: post(message, cta_url) [timeout=8s]
        Mastodon->>Mastodon: POST /api/v1/statuses (Bearer)
        Mastodon-->>Service: PlatformResult(success, url_4)
    and
        Service->>Telegram: post(message, cta_url) [timeout=8s]
        Telegram->>Telegram: POST /sendMessage (Bot token)
        Telegram-->>Service: PlatformResult(success, url_5)
    end

    Service->>Service: Aggregate outcomes (5 success, 0 failed)
    Service-->>Router: PostResponse(success=True, 5 results)
    Router-->>Client: HTTP 200 OK JSON Telemetry
```

---

## 2. Sequence 2: Partial Failure & Fault Isolation (Bulkhead Pattern)

Demonstrates how the engine isolates failures. In this scenario:
- **Dev.to** and **Mastodon** succeed.
- **LinkedIn** returns HTTP 401 (token expired).
- **Telegram** returns HTTP 400 (bot not admin).
- **Hashnode** hangs and times out at 8.0 seconds.
- The overall system remains resilient and returns HTTP 200 with itemized diagnoses.

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant Router as app/main.py
    participant Service as app/services/posting_service.py
    participant LinkedIn as LinkedInPlatform
    participant DevTo as DevToPlatform
    participant Hashnode as HashnodePlatform
    participant Mastodon as MastodonPlatform
    participant Telegram as TelegramPlatform

    Client->>Router: POST /posting
    Router->>Service: post_to_all(message, cta_url)

    par Parallel Execution
        Service->>LinkedIn: post()
        LinkedIn-->>Service: PlatformResult(status="failed", error="OAuth token expired")
    and
        Service->>DevTo: post()
        DevTo-->>Service: PlatformResult(status="success", url="https://dev.to/...")
    and
        Service->>Hashnode: post() (Stalls for >8s)
        Note over Service,Hashnode: asyncio.wait_for triggers after 8.0s Timeout
        Service->>Service: Catch TimeoutError
        Service->>Service: PlatformResult(status="failed", error="Platform timeout after 8s")
    and
        Service->>Mastodon: post()
        Mastodon-->>Service: PlatformResult(status="success", url="https://mastodon.social/...")
    and
        Service->>Telegram: post()
        Telegram-->>Service: PlatformResult(status="failed", error="Bot not channel admin")
    end

    Service->>Service: Aggregate (2 success, 3 failed)
    Service-->>Router: PostResponse(success=True, successful_posts=2, failed_posts=3)
    Router-->>Client: HTTP 200 OK (With Complete Diagnostics)
```

---

## 3. Sequence 3: Ingress Validation Failure

Demonstrates immediate short-circuiting when input violates invariants (e.g. 2 CTA links submitted). Zero network traffic is dispatched to external platforms.

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant FastAPI as FastAPI ASGI Engine
    participant Pydantic as app/schemas.py (PostRequest)

    Client->>FastAPI: POST /posting { "message": "Two links: https://a.com and https://b.com" }
    FastAPI->>Pydantic: Parse and Validate PostRequest
    Pydantic->>Pydantic: validate_content_and_url()
    Note over Pydantic: Regex detects 2 URLs -> Invariant INV-002 Violated
    Pydantic-->>FastAPI: Raise ValueError("Message contains 2 URLs. Exactly 1 required.")
    FastAPI-->>Client: HTTP 422 Unprocessable Entity
    Note over Client: Execution ends in <5ms with zero external network overhead
```


---

## 4. Sequence 4: Ingress SSRF & Trojan Source Sanitization Interception

Demonstrates how the 7-stage Ingress Sanitization pipeline intercepts malicious payloads (e.g. cloud metadata IP `http://169.254.169.254` or Trojan Source bidi override characters `\u202E`) and formats an RFC 7807 Problem Details response without invoking downstream adapters:

```mermaid
sequenceDiagram
    autonumber
    actor Attacker as Untrusted Inbound Client
    participant Ingress as FastAPI Router
    participant Sanitizer as Pydantic v2 Ingress Sanitizer
    participant Handler as Global Exception Handler

    Attacker->>Ingress: POST /posting { "message": "Explore http://169.254.169.254/latest/meta-data/" }
    Ingress->>Sanitizer: sanitize_raw_input() & validate_invariants_and_ssrf()
    
    Sanitizer->>Sanitizer: Stage 2-3: Normalize Unicode to NFKC
    Sanitizer->>Sanitizer: Stage 4: Verify absence of Trojan Source bidi chars
    Sanitizer->>Sanitizer: Stage 6: Extract CTA URL -> http://169.254.169.254
    Sanitizer->>Sanitizer: Stage 7: Evaluate destination IP against Link-Local Subnet
    
    note over Sanitizer: IP 169.254.169.254 is Link-Local Cloud Metadata!
    Sanitizer-->>Ingress: Raise SSRFProhibitedException("Destination IP is in prohibited metadata range")
    Ingress->>Handler: Catch SSRFProhibitedException
    Handler-->>Attacker: HTTP 422 (RFC 7807: ERR_SSRF_PROHIBITED)
    note over Attacker: Terminated in <2ms with zero outbound HTTP dispatch
```
