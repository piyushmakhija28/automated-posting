# Level 9: Agile Governance & Management — Work Breakdown Structure (WBS) & Sprint Backlog

**Document ID:** `DOC-MGT-01-WBS`  
**Project:** `automated-posting`  
**Author:** Principal Software Architect & Staff Systems Engineer  
**Status:** APPROVED & SYNCHRONIZED WITH GITHUB ISSUES  
**Standard:** Agile Scrum, INVEST Story Methodology, WSJF Prioritization, GitHub Milestones  

---

## 1. Work Breakdown Structure (WBS)

```
1.0 Automated Multi-Platform Posting Engine
    ├── 1.1 Ingress & Hardening (Sprint 1)
    │   ├── 1.1.1 Core Constants Segregation (Validation, Service, API, Platform)
    │   ├── 1.1.2 12-Factor Settings Configuration (.env.example & pydantic-settings)
    │   ├── 1.1.3 Centralized Logging with SensitiveDataFilter Token Masker
    │   ├── 1.1.4 Domain & Infrastructure Exception Hierarchy (RFC 7807 Mappings)
    │   ├── 1.1.5 Ingress PostingForm with 7-Stage Ordered Validation Pipeline
    │   └── 1.1.6 Egress DTO Representations (PostingResponseDto, PlatformResultDto)
    ├── 1.2 Platform Ports & Adapters Layer (Sprint 2)
    │   ├── 1.2.1 Abstract BasePlatformAdapter Port & Timestamp Utilities
    │   ├── 1.2.2 AdapterRegistry Factory for Dependency-Injected Instantiation
    │   ├── 1.2.3 LinkedIn UGC Posts Adapter (OAuth 2.0 REST API v2)
    │   ├── 1.2.4 Dev.to Articles Adapter (Forem REST API & Dynamic Title Generator)
    │   ├── 1.2.5 Hashnode Publication Adapter (GraphQL API Mutation publishPost)
    │   ├── 1.2.6 Mastodon Statuses Adapter (Statuses REST API v1 & Idempotency Keys)
    │   └── 1.2.7 Telegram Bot Adapter (Bot API sendMessage & HTML Entity Escaping)
    ├── 1.3 Concurrency & Resilience Engine (Sprint 3)
    │   ├── 1.3.1 PostingService Interface & PostingServiceImpl Implementation
    │   ├── 1.3.2 Asyncio.gather Bulkhead Concurrency (return_exceptions=False in Safe Execute)
    │   ├── 1.3.3 Per-Adapter 3.0s SLA Timeout Guard (asyncio.wait_for)
    │   ├── 1.3.4 Global 5.0s Gateway Deadline Guard
    │   └── 1.3.5 PostingServiceHelper (DTO Mapping, Tallies & Status Computation)
    ├── 1.4 Web Layer & SRE Endpoints (Sprint 4)
    │   ├── 1.4.1 Ingress POST /posting Endpoint with Dependency Injection
    │   ├── 1.4.2 SRE Probes: Liveness GET /health & Readiness GET /ready
    │   ├── 1.4.3 FastAPI App Factory create_app() & Lifespan Context Manager
    │   ├── 1.4.4 Shared Connection-Pooled HTTPX AsyncClient with Limits
    │   └── 1.4.5 Centralized Global RFC 7807 Exception Handlers
    ├── 1.5 Triad Automated Testing Suite (Sprint 4)
    │   ├── 1.5.1 Shared Pytest Fixture Harness (conftest.py with ASGITransport)
    │   ├── 1.5.2 Bootstrap & Lifespan Tests (test_bootstrap.py)
    │   ├── 1.5.3 Ingress Router Triad Tests: 200, 422, 400, 429, 504 (test_router_posting.py)
    │   ├── 1.5.4 SRE Probe Tests: /health & /ready (test_router_health.py)
    │   ├── 1.5.5 7-Stage Validation Pipeline Tests (test_validation_pipeline.py)
    │   ├── 1.5.6 Concrete Platform Adapter Tests with Mock Responses (test_adapters.py)
    │   ├── 1.5.7 Bulkhead Fault Isolation & Timeout Resilience Tests (test_resilience_bulkhead.py)
    │   └── 1.5.8 Code Coverage Gate Enforcement (>= 90% via pytest-cov)
    └── 1.6 Production Operations & DevOps (Sprint 5)
        ├── 1.6.1 Hardened Multi-Stage Non-Root OCI Dockerfile
        ├── 1.6.2 Docker Healthcheck & Security Configuration
        ├── 1.6.3 GitHub Actions Automated CI/CD Pipeline (.github/workflows/ci-cd.yml)
        ├── 1.6.4 Strict Type Checking (mypy --strict) & Ruff Linting
        └── 1.6.5 Live Cloud Deployment & Smoke Test Verification
```

---

## 2. Sprint Milestones & GitHub Issues Matrix

| Milestone | Sprint Title | Focus Area | Target Due Date | Linked Issues |
|:---|:---|:---|:---:|:---|
| **Milestone 1** | **Sprint 1: Core Foundation & Ingress Pipeline** | Infrastructure, Typed Constants, Exceptions, Logging, Forms & 7-Stage Validation | 2026-11-19 | #2 |
| **Milestone 2** | **Sprint 2: Platform Ports & Adapter Layer** | BasePort, AdapterRegistry Factory, 5 Concrete Platform Adapters | 2026-11-20 | #3, #4, #8, #9, #10, #11, #12 |
| **Milestone 3** | **Sprint 3: Concurrency Engine & Bulkhead Resilience** | PostingService ABC, PostingServiceImpl (Bulkhead), Helper, SLA Timeouts | 2026-11-21 | #5 |
| **Milestone 4** | **Sprint 4: Routers, SRE Probes & Triad Testing** | Routers (`/posting`, `/health`, `/ready`), Lifespan, Triad Test Suite ($\ge 90\%$) | 2026-11-21 | #6, #7 |
| **Milestone 5** | **Sprint 5: Production Docker, CI/CD & Deployment** | Multi-stage Docker, GitHub Actions CI/CD, Quality Gates, Cloud Smoke Tests | 2026-11-22 | #13, #14 |

---

## 3. Comprehensive Sprint Backlog & Story Specifications

### Sprint 1: Core Foundation & Ingress Pipeline (Milestone 1 — Due 19 Nov)

#### [Issue #2](https://github.com/piyushmakhija28/automated-posting/issues/2) — [Feature] US-01: Ingress Schema, 7-Stage Sanitization & Validation Engine
* **Story Points:** 3 | **WSJF:** 20 | **Labels:** `backend`, `security`, `validation`, `sprint-1`
* **Target Files:**
  - `app/core/constants.py`
  - `app/core/config.py`
  - `app/core/exceptions.py`
  - `app/core/logging.py`
  - `app/models/forms/posting_form.py`
  - `app/models/dtos/platform_dto.py`
  - `app/models/dtos/posting_dto.py`
  - `app/models/dtos/problem_dto.py`
  - `tests/test_validation_pipeline.py`
* **Detailed Acceptance Criteria:**
  - [ ] `ValidationMessageConstants`, `ServiceMessageConstants`, `ApiConstants`, and `PlatformConstants` defined without magic strings.
  - [ ] `Settings` parses 12-factor environment variables via `pydantic-settings` with default fallbacks.
  - [ ] `SensitiveDataFilter` masks Bearer tokens, API keys, and Telegram bot tokens in structured JSON logs.
  - [ ] `PostingForm` executes 7-stage sequential validation in `@field_validator("message", mode="before")`.
  - [ ] Rejects 0 URLs (`ValidationMessageConstants.MSG_URL_REQUIRED`) and $>1$ URLs (`MSG_URL_MULTIPLE`).
  - [ ] Screens loopback and private IP literals preventing SSRF.
  - [ ] Normalizes Unicode via NFKC and strips zero-width spaces (`\u200B`..`\u200D`, `\uFEFF`, `\u00AD`).
  - [ ] Rejects prompt injection patterns with `SecurityThreatError`.

---

### Sprint 2: Platform Ports & Adapter Layer (Milestone 2 — Due 20 Nov)

#### [Issue #3](https://github.com/piyushmakhija28/automated-posting/issues/3) — [Feature] US-02: Base Adapter Contract & AdapterRegistry Factory
* **Story Points:** 2 | **WSJF:** 19 | **Labels:** `architecture`, `backend`, `sprint-2`
* **Target Files:**
  - `app/platforms/base.py`
  - `app/platforms/registry.py`
* **Detailed Acceptance Criteria:**
  - [ ] `BasePlatformAdapter` abstract base class defines `name`, `client`, `is_configured() -> bool`, and `post(message, cta_url) -> PlatformResultDto`.
  - [ ] Shared utilities `_extract_date_time()` and `_handle_error(exc)` implemented.
  - [ ] `AdapterRegistry` registers platform classes and instantiates them via `create_all(client, settings)`.
  - [ ] Adheres strictly to Open/Closed Principle (OCP) and Dependency Inversion Principle (DIP).

#### [Issue #4](https://github.com/piyushmakhija28/automated-posting/issues/4) — [Epic] Platform Adapters Suite (US-03 to US-07)
* **Parent Tracker** for child stories #8, #9, #10, #11, #12.

#### [Issue #8](https://github.com/piyushmakhija28/automated-posting/issues/8) — [Feature] US-03: LinkedIn UGC Post Adapter (OAuth 2.0 UGC API v2)
* **Story Points:** 5 | **WSJF:** 17 | **Labels:** `backend`, `integrations`, `sprint-2`
* **Target Files:** `app/platforms/linkedin.py`, `tests/test_adapters.py`
* **Detailed Acceptance Criteria:**
  - [ ] Post payload to `https://api.linkedin.com/v2/ugcPosts` with `Authorization: Bearer {token}`.
  - [ ] Ingests `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_PERSON_URN`.
  - [ ] Extracts `id` from `X-RestLi-Id` header and generates `https://www.linkedin.com/feed/update/{urn}`.
  - [ ] Returns `status="skipped"` when credentials are omitted.

#### [Issue #9](https://github.com/piyushmakhija28/automated-posting/issues/9) — [Feature] US-04: Dev.to Article Adapter (Forem REST API)
* **Story Points:** 3 | **WSJF:** 17 | **Labels:** `backend`, `integrations`, `sprint-2`
* **Target Files:** `app/platforms/devto.py`, `tests/test_adapters.py`
* **Detailed Acceptance Criteria:**
  - [ ] Implements `_synthesize_title(message)` extracting first sentence $\le 60$ chars.
  - [ ] Posts to `https://dev.to/api/articles` with `api-key: {key}` header.
  - [ ] Formats body in Markdown appending `[Read More]({cta_url})`.
  - [ ] Returns `post_url` from response `url`.

#### [Issue #10](https://github.com/piyushmakhija28/automated-posting/issues/10) — [Feature] US-05: Hashnode Publication Adapter (GraphQL API)
* **Story Points:** 5 | **WSJF:** 17 | **Labels:** `backend`, `integrations`, `sprint-2`
* **Target Files:** `app/platforms/hashnode.py`, `tests/test_adapters.py`
* **Detailed Acceptance Criteria:**
  - [ ] Posts authenticated GraphQL `publishPost` mutation to `https://gql.hashnode.com`.
  - [ ] Binds `HASHNODE_API_KEY` and `HASHNODE_PUBLICATION_ID`.
  - [ ] Extracts `data.publishPost.post.id` and `url`.
  - [ ] Traps GraphQL error arrays without raising unhandled exceptions.

#### [Issue #11](https://github.com/piyushmakhija28/automated-posting/issues/11) — [Feature] US-06: Mastodon Status Adapter (Statuses API v1)
* **Story Points:** 3 | **WSJF:** 16 | **Labels:** `backend`, `integrations`, `sprint-2`
* **Target Files:** `app/platforms/mastodon.py`, `tests/test_adapters.py`
* **Detailed Acceptance Criteria:**
  - [ ] Posts status update to `{base_url}/api/v1/statuses` with `Idempotency-Key` header.
  - [ ] Ingests `MASTODON_ACCESS_TOKEN` and configurable `MASTODON_BASE_URL`.
  - [ ] Returns toot `id` and `url`.

#### [Issue #12](https://github.com/piyushmakhija28/automated-posting/issues/12) — [Feature] US-07: Telegram Channel Bot Adapter (Bot API sendMessage)
* **Story Points:** 3 | **WSJF:** 16 | **Labels:** `backend`, `integrations`, `sprint-2`
* **Target Files:** `app/platforms/telegram.py`, `tests/test_adapters.py`
* **Detailed Acceptance Criteria:**
  - [ ] Posts to `https://api.telegram.org/bot{token}/sendMessage` with `parse_mode="HTML"`.
  - [ ] Ingests `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHANNEL_ID`.
  - [ ] Escapes HTML control characters in message text.
  - [ ] Constructs public URL `https://t.me/{channel}/{message_id}` for public channels.

---

### Sprint 3: Concurrency Engine & Bulkhead Resilience (Milestone 3 — Due 21 Nov)

#### [Issue #5](https://github.com/piyushmakhija28/automated-posting/issues/5) — [Feature] US-08: Concurrency Fan-Out, Bulkhead Isolation & Dual-Tier Timeout Engine
* **Story Points:** 5 | **WSJF:** 20 | **Labels:** `backend`, `resilience`, `concurrency`, `sprint-3`
* **Target Files:**
  - `app/services/posting_service.py`
  - `app/services/posting_helper.py`
  - `tests/test_service_posting.py`
  - `tests/test_resilience_bulkhead.py`
* **Detailed Acceptance Criteria:**
  - [ ] `PostingService` ABC defines `broadcast(form, correlation_id) -> PostingResponseDto`.
  - [ ] `PostingServiceImpl` executes concurrent tasks via `asyncio.gather(*tasks, return_exceptions=False)`.
  - [ ] `_safe_execute` isolates errors per adapter with `asyncio.wait_for(..., timeout=3.0)`.
  - [ ] Platform exceptions or timeouts map to `PlatformResultDto(status="failed", error=...)` without propagating to peer coroutines.
  - [ ] `PostingServiceHelper` builds immutable `PostingResponseDto` and calculates `total_latency_ms`.

---

### Sprint 4: Routers, SRE Probes & Triad Testing (Milestone 4 — Due 21 Nov)

#### [Issue #6](https://github.com/piyushmakhija28/automated-posting/issues/6) — [Feature] US-09: FastAPI Ingress Router, SRE Probes & Global RFC 7807 Handlers
* **Story Points:** 3 | **WSJF:** 18 | **Labels:** `backend`, `api`, `sre`, `sprint-4`
* **Target Files:**
  - `app/routers/posting.py`
  - `app/routers/health.py`
  - `app/main.py`
  - `tests/test_router_posting.py`
  - `tests/test_router_health.py`
* **Detailed Acceptance Criteria:**
  - [ ] `POST /posting` handles ingress validation, calls `PostingService`, and populates `X-Correlation-ID` and `X-Response-Time-Ms` headers.
  - [ ] Zero business logic inside routers.
  - [ ] `GET /health` returns 200 OK with `{"status": "UP"}`.
  - [ ] `GET /ready` returns 200 OK with `{"status": "READY"}`.
  - [ ] Global exception handlers map `ApplicationException` and `RequestValidationError` to RFC 7807 `ProblemDetailsDto`.
  - [ ] Lifespan manages shared `httpx.AsyncClient` lifecycle with connection pooling (`limits=httpx.Limits(max_keepalive_connections=20)`).

#### [Issue #7](https://github.com/piyushmakhija28/automated-posting/issues/7) — [Feature] US-10: Triad Automated Testing Suite (Positive, Negative, Edge-Case >= 90% Coverage)
* **Story Points:** 5 | **WSJF:** 19 | **Labels:** `testing`, `qa`, `coverage`, `sprint-4`
* **Target Files:**
  - `tests/conftest.py`
  - `tests/test_bootstrap.py`
  - `tests/test_router_posting.py`
  - `tests/test_router_health.py`
  - `tests/test_service_posting.py`
  - `tests/test_validation_pipeline.py`
  - `tests/test_adapters.py`
  - `tests/test_resilience_bulkhead.py`
* **Detailed Acceptance Criteria:**
  - [ ] Shared fixtures in `conftest.py` provide `mock_posting_service`, `app_with_mock_service`, `client`, and `async_client`.
  - [ ] Triad coverage: Positive, Negative, Edge-Case implemented across all layers.
  - [ ] `pytest --cov=app --cov-fail-under=90` passes with zero failures.
  - [ ] All mock tests run in $< 5$ seconds without making live internet requests.

---

### Sprint 5: Production Docker, CI/CD & Deployment (Milestone 5 — Due 22 Nov)

#### [Issue #13](https://github.com/piyushmakhija28/automated-posting/issues/13) — [Feature] US-11: Multi-Stage OCI Containerization & Dockerfile Hardening
* **Story Points:** 3 | **WSJF:** 18 | **Labels:** `devops`, `docker`, `sprint-5`
* **Target Files:** `Dockerfile`, `.dockerignore`
* **Detailed Acceptance Criteria:**
  - [ ] Multi-stage build compiles dependencies in `builder` stage and produces minimal `python:3.11-slim` runtime image.
  - [ ] Non-root execution under user `appuser:10001`.
  - [ ] Final image size $< 200\text{ MB}$.
  - [ ] Built-in Docker `HEALTHCHECK` configured against `/health`.

#### [Issue #14](https://github.com/piyushmakhija28/automated-posting/issues/14) — [Feature] US-12: GitHub Actions Automated CI/CD Pipeline & Quality Gate
* **Story Points:** 3 | **WSJF:** 18 | **Labels:** `ci-cd`, `devops`, `quality-gate`, `sprint-5`
* **Target Files:** `.github/workflows/ci-cd.yml`
* **Detailed Acceptance Criteria:**
  - [ ] Automated workflow triggers on push to `main` and pull requests.
  - [ ] Executes `ruff check`, `black --check`, and `mypy app/ --strict`.
  - [ ] Runs full test suite enforcing $\ge 90\%$ statement/branch coverage.
  - [ ] Builds Docker image and verifies container health check.

---

## 4. Definition of Done (DoD)

A user story or feature is marked **DONE** only when:
1. **Implementation:** Code adheres strictly to Level 2.2 Docstrings-Only convention, typed constants, and DTO/Form separation. Zero inline narration comments.
2. **Type Safety:** Passes static type checking with zero errors via `mypy app/ --strict`.
3. **Style & Linting:** Passes `ruff check app/ tests/` and `black --check app/ tests/`.
4. **Automated Testing:** Unit and integration tests written covering Positive, Negative, and Edge-Case scenarios with $\ge 90\%$ test coverage.
5. **Security Verification:** Zero hardcoded credentials; all secrets masked in logs via `SensitiveDataFilter`.
6. **Documentation Sync:** WBS, Traceability Matrix, and README updated to reflect changes.
7. **Git Commit Standard:** Dedicated commit referencing the GitHub Issue number (`feat/fix: descriptive title (#N)`).
