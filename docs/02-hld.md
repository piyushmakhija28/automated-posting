# Level 1: Solution Architecture & High-Level Design (HLD)

**Document ID:** `DOC-02-HLD`  
**Project:** `automated-posting`  
**Author:** Principal Software Architect
**Reviewer:** Staff Backend Engineering Lead
**Approver:** Technical Architecture Board
**Status:** APPROVED  
**Standard:** C4 Architectural Model, ISO/IEC/IEEE 42010

---

## 1. Architectural Style & Core Design Principles

The Automated Multi-Platform Posting Engine is architected around **Clean Architecture**, **Hexagonal (Ports and Adapters)** principles, and **Reactive Asynchronous Non-Blocking I/O**.

### Key Architectural Tenets:
1. **Unidirectional Dependency Flow:** Ingress controllers depend on service interfaces; services depend on platform abstraction ports; concrete platform adapters implement the ports. The core domain never depends on external platform SDKs.
2. **Bulkhead Isolation (Failure Containment):** Each external platform interaction is isolated in its own coroutine execution boundary. The failure, timeout, or rate-limiting of any single platform cannot cascade or affect others.
3. **Stateless Concurrency:** The service layer maintains zero mutable in-memory state across requests, guaranteeing thread-safety and race-condition immunity under high-concurrency loads.
4. **Zero-Trust Security & Observability:** All sensitive credentials are externalized to environment variables and injected at boot time. Telemetry components automatically scrub tokens before emitting logs.

---

## 2. C4 Architecture Model

### 2.1 C4 Level 1: System Context Diagram
The System Context defines the boundary of our engine and its interactions with human actors and external third-party platform APIs.

```mermaid
graph TD
    Client[API Client / Marketing Automation / CI/CD] -->|POST /posting JSON Payload| PostingEngine[Automated Multi-Platform Posting Engine]
    
    PostingEngine -->|OAuth 2.0 UGC Post API| LinkedIn[LinkedIn API]
    PostingEngine -->|REST Articles API| DevTo[Dev.to API]
    PostingEngine -->|GraphQL publishPost Mutation| Hashnode[Hashnode GraphQL API]
    PostingEngine -->|REST Statuses API| Mastodon[Mastodon Instance API]
    PostingEngine -->|Bot API sendMessage| Telegram[Telegram Bot API]
    
    Admin[DevOps / SRE] -->|GET /health, /ready| PostingEngine
```

---

### 2.2 C4 Level 2: Container Diagram
The Container Diagram illustrates the high-level technical choices and execution boundaries within the runtime environment.

```mermaid
graph TB
    subgraph HostContainer [Docker Linux Container]
        subgraph ServerProcess [Uvicorn ASGI Server]
            FastAPIApp[FastAPI Web Application Layer]
            ConfigModule[Pydantic Settings & Env Manager]
            SanitizedLog[Sanitized Logger & Log Masker]
        end
        
        subgraph AsyncEngine [Python Asyncio Event Loop]
            PostService[Posting Orchestration Service]
            HttpEngine[HTTPX AsyncClient Connection Pool]
        end
    end
    
    Client -->|HTTPS :4000| FastAPIApp
    FastAPIApp --> ConfigModule
    FastAPIApp --> SanitizedLog
    FastAPIApp --> PostService
    PostService --> HttpEngine
    
    HttpEngine -->|TLS Outbound| LinkedIn
    HttpEngine -->|TLS Outbound| DevTo
    HttpEngine -->|TLS Outbound| Hashnode
    HttpEngine -->|TLS Outbound| Mastodon
    HttpEngine -->|TLS Outbound| Telegram
```

---

### 2.3 C4 Level 3: Component Diagram
The Component Diagram details the internal modular decomposition inside the FastAPI application.

```mermaid
graph TD
    subgraph WebLayer [Routing & Ingress Layer]
        Router[app/main.py: /posting Router]
        HealthRouter[app/main.py: /health, /ready]
        ReqModel[app/schemas.py: PostRequest]
        RespModel[app/schemas.py: PostResponse, PlatformResult]
    end
    
    subgraph ValidationLayer [Ingress Hardening Layer]
        Validator[app/utils/validators.py: URL & Length Validator]
        Sanitizer[app/utils/logger.py: Bearer Token Redactor]
    end
    
    subgraph ServiceLayer [Domain Orchestration Layer]
        PostingService[app/services/posting_service.py]
    end
    
    subgraph AdapterLayer [Platform Ports & Adapters Layer]
        BaseAdapter[app/platforms/base.py: BasePlatform Interface]
        LinkedInAdapter[app/platforms/linkedin.py]
        DevtoAdapter[app/platforms/devto.py]
        HashnodeAdapter[app/platforms/hashnode.py]
        MastodonAdapter[app/platforms/mastodon.py]
        TelegramAdapter[app/platforms/telegram.py]
    end
    
    Router --> ReqModel
    Router --> Validator
    Router --> PostingService
    Router --> RespModel
    
    PostingService --> BaseAdapter
    BaseAdapter <|-- LinkedInAdapter
    BaseAdapter <|-- DevtoAdapter
    BaseAdapter <|-- HashnodeAdapter
    BaseAdapter <|-- MastodonAdapter
    BaseAdapter <|-- TelegramAdapter
    
    LinkedInAdapter --> Sanitizer
    DevtoAdapter --> Sanitizer
    HashnodeAdapter --> Sanitizer
    MastodonAdapter --> Sanitizer
    TelegramAdapter --> Sanitizer
```

---

### 2.4 C4 Level 4: Code & Class Blueprint

```
BasePlatform (Abstract Base Class)
  ├── name: str (Property)
  ├── is_configured() -> bool
  └── async post(message: str, cta_url: str) -> PlatformResult

PlatformResult (Pydantic v2 Model)
  ├── platform: str
  ├── status: str ("success" | "failed")
  ├── posted_url: Optional[str]
  ├── public_access: bool
  ├── date: Optional[str] (YYYY-MM-DD)
  ├── time: Optional[str] (HH:MM:SS)
  └── error: Optional[str]

PostRequest (Pydantic v2 Model)
  └── message: str (Field max_length=200)
      └── @field_validator("message") -> extracts & validates exactly 1 URL

PostingService (Domain Service)
  ├── adapters: list[BasePlatform]
  └── async post_to_all(message: str, cta_url: str) -> PostResponse
      └── asyncio.gather(*[safe_execute(adapter) for adapter in adapters])
```

---

## 3. Concurrency & Fan-Out Architecture

### Non-Blocking Asynchronous Fan-Out
To ensure minimum latency and prevent any single platform from blocking the main execution path, the posting service executes all adapters concurrently:

```python
async def _execute_adapter(adapter: BasePlatform, message: str, cta_url: str) -> PlatformResult:
    try:
        # Enforce per-adapter 8.0-second timeout
        return await asyncio.wait_for(
            adapter.post(message, cta_url),
            timeout=8.0
        )
    except asyncio.TimeoutError:
        return PlatformResult(
            platform=adapter.name,
            status="failed",
            posted_url=None,
            public_access=False,
            date=None,
            time=None,
            error="Platform timeout after 8.0s"
        )
    except Exception as exc:
        return PlatformResult(
            platform=adapter.name,
            status="failed",
            posted_url=None,
            public_access=False,
            date=None,
            time=None,
            error=str(exc)
        )
```

### Execution Latency Model:
Given $N=5$ platforms with latencies $L_1, L_2, L_3, L_4, L_5$:
$$\text{Total Latency} \approx \max(L_1, L_2, L_3, L_4, L_5) + \epsilon_{\text{overhead}} \ll \sum_{i=1}^{5} L_i$$
Under sequential execution, total latency would be $2.1\text{s} + 1.2\text{s} + 1.5\text{s} + 0.8\text{s} + 0.4\text{s} = 6.0\text{s}$.  
Under concurrent execution, total latency is $\max(2.1, 1.2, 1.5, 0.8, 0.4) \approx 2.1\text{s}$.

---

## 4. Resiliency & Fault Isolation (Bulkhead Pattern)

The system incorporates the **Bulkhead Pattern** inspired by naval ship hull design:

```
[ Ingress POST /posting ]
          │
    ┌─────┴───────────────────────────────────────────────────────┐
    │ asyncio.gather with Isolated Exception & Timeout Boundaries │
    ├─────────────┬─────────────┬─────────────┬─────────────┬─────┤
    │  LinkedIn   │   Dev.to    │  Hashnode   │  Mastodon   │ Telegram │
    │   Adapter   │   Adapter   │   Adapter   │   Adapter   │ Adapter  │
    │  [Timeout:  │  [Timeout:  │  [Timeout:  │  [Timeout:  │[Timeout: │
    │    8.0s]    │    8.0s]    │    8.0s]    │    8.0s]    │  8.0s]   │
    └─────────────┴─────────────┴─────────────┴─────────────┴─────┘
          │             │             │             │          │
     (SUCCESS)     (SUCCESS)      (HTTP 401)    (SUCCESS)  (SUCCESS)
          │             │             │             │          │
    └─────┬─────────────┴─────────────┴─────────────┴──────────┘
          ▼
[ Aggregate Results: 4 Successful, 1 Failed -> HTTP 200 Telemetry ]
```

- If Hashnode returns HTTP 401 (bad API key), it catches the exception, records the diagnostic error, and returns a failed `PlatformResult`.
- LinkedIn, Dev.to, Mastodon, and Telegram complete normally.
- The top-level response emits `HTTP 200 OK` with `success: true, total_platforms: 5, successful_posts: 4, failed_posts: 1`.

---

## 5. Security Architecture & Threat Surface

1. **Ingress Hardening (OWASP API4:2023):** Input bounded strictly at 200 characters to prevent memory exhaustion and buffer overflows.
2. **SSRF Defense (OWASP API7:2023):** Extracted URLs are **never fetched** by our backend server. They are parsed syntactically and forwarded as plain-text payloads to third-party APIs.
3. **Log Sanitization (OWASP API2:2023 / RFC 5424):** A custom logging handler scrubs authorization patterns (`Bearer [A-Za-z0-9_\-\.]+`) before any message reaches stdout.
4. **Environment Isolation (12-Factor App):** All credentials (`LINKEDIN_ACCESS_TOKEN`, `DEVTO_API_KEY`, `HASHNODE_API_KEY`, `MASTODON_ACCESS_TOKEN`, `TELEGRAM_BOT_TOKEN`) are injected via environment variables.

---

## 6. SRE & Observability Strategy

1. **Distributed Request Tracing:** Every HTTP request receives or generates a unique correlation ID (`X-Request-ID`), propagated across all log statements.
2. **Health Inspection Probes:**
   - `GET /health`: Liveness probe indicating server process is healthy.
   - `GET /ready`: Readiness probe verifying environment configuration and outbound connectivity.
3. **Cold-Start Mitigation for PaaS Deployment:** Render.com free-tier instances sleep after 15 minutes. The architecture includes a lightweight pinging strategy to maintain readiness during test evaluation.
