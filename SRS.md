# Software Requirements Specification

## 1. Purpose
The purpose of the **Automated Multi-Platform Posting System** is to provide an asynchronous, highly-resilient REST API service that automates the concurrent publication of short promotional messages across diverse third-party developer, business, and social media platforms. Built with Python 3.x and FastAPI, the system accepts a single message containing an embedded Call-to-Action (CTA) link, validates input integrity and security parameters, dynamically dispatches the content in parallel to 5+ platforms (LinkedIn, Dev.to, Hashnode, Mastodon, Telegram), and provides structured telemetry regarding posting status, published URLs, and diagnostic information without leaking sensitive credentials.

---

## 2. Scope
### 2.1 In Scope
- Single endpoint `POST /posting` listening locally on port 4000.
- Rigorous multi-tier input validation: message length $\le 200$ characters, exactly one valid HTTP/HTTPS URL, and protocol validation.
- Concurrency engine executing non-blocking parallel dispatches via `asyncio.gather(..., return_exceptions=True)`.
- Five concrete platform integrations:
  - LinkedIn (UGC Posts API via OAuth 2.0).
  - Dev.to (Forem Articles API with dynamic title generation).
  - Hashnode (GraphQL `publishPost` mutation with publication binding).
  - Mastodon (Statuses REST API on federated instances).
  - Telegram (Bot API `sendMessage` to public channels).
- Bulkhead fault isolation: failure or timeout of one platform does not abort others.
- Granular 8.0-second per-adapter timeout handling and overall 10.0-second SLA governance.
- Security architecture enforcing OWASP API Security Top 10 standards, SSRF defense, and automated log token masking.
- Health inspection endpoints (`GET /health`, `GET /ready`).
- Automated test suite achieving $\ge 90\%$ code coverage using `pytest` and `httpx.MockTransport`.
- Multi-stage containerized deployment configuration for Render.com PaaS.

### 2.2 Out of Scope
- Direct client selection or toggling of target platforms via request headers or query parameters.
- Integrations with paid-tier-only platforms (such as Twitter/X v2 write tier) or platforms requiring multi-week enterprise approvals (such as Meta Facebook Pages).
- Multi-tenant persistent database storage or historical post versioning.
- Media attachment parsing (images, videos, PDF documents).

---

## 3. Requirements

### 3.1 Functional Requirements

**FR-001:** The system SHALL expose an asynchronous HTTP POST endpoint at `/posting` accepting `application/json`.
- Priority: High
- Source: Practical Test Section 2
- Added: 2026-11-18

**FR-002:** The system SHALL validate that the incoming `message` string does not exceed 200 unicode characters.
- Priority: High
- Source: Practical Test Section 2
- Added: 2026-11-18

**FR-003:** The system SHALL validate that the incoming `message` string contains exactly one valid HTTP or HTTPS URL.
- Priority: High
- Source: Practical Test Section 2
- Added: 2026-11-18

**FR-004:** The system SHALL strip trailing punctuation (`.,;:!?)'`) from extracted URLs and reject bare domains lacking `http://` or `https://` schemas.
- Priority: Medium
- Source: Architecture Feasibility Finding FEAS-007
- Added: 2026-11-18

**FR-005:** The system SHALL autonomously orchestrate message distribution across all configured platform adapters without requiring client-side platform routing.
- Priority: High
- Source: Practical Test Section 3.A
- Added: 2026-11-18

**FR-006:** The system SHALL integrate with LinkedIn's UGC Posts API using OAuth 2.0 Bearer tokens to publish social feed updates.
- Priority: High
- Source: Practical Test Section 3.A
- Added: 2026-11-18

**FR-007:** The system SHALL integrate with Dev.to's Articles API, synthesizing a title from the initial 60 characters and wrapping the message as markdown body.
- Priority: High
- Source: Architecture Feasibility Finding FEAS-002
- Added: 2026-11-18

**FR-008:** The system SHALL integrate with Hashnode's GraphQL API (`https://gql.hashnode.com`), dispatching a `publishPost` mutation with target publication ID.
- Priority: High
- Source: Architecture Feasibility Finding FEAS-003
- Added: 2026-11-18

**FR-009:** The system SHALL integrate with Mastodon's REST statuses API, dispatching status updates to the configured instance.
- Priority: High
- Source: Practical Test Section 3.A
- Added: 2026-11-18

**FR-010:** The system SHALL integrate with Telegram's Bot API, sending formatted messages to a specified public channel username.
- Priority: High
- Source: Practical Test Section 3.A
- Added: 2026-11-18

**FR-011:** The system SHALL execute all platform posting operations concurrently using `asyncio.gather(..., return_exceptions=True)`.
- Priority: High
- Source: Architecture Feasibility Finding FEAS-004
- Added: 2026-11-18

**FR-012:** The system SHALL isolate platform failures such that an unhandled exception or HTTP error in one adapter does not prevent remaining adapters from executing.
- Priority: High
- Source: Practical Test Section 3.A
- Added: 2026-11-18

**FR-013:** The system SHALL enforce an 8.0-second execution timeout on each individual platform adapter using `asyncio.wait_for`.
- Priority: High
- Source: Architecture Feasibility Finding FEAS-005
- Added: 2026-11-18

**FR-014:** The system SHALL intercept HTTP 429 rate limit responses, extract `Retry-After` headers where available, and output structured error diagnostics.
- Priority: Medium
- Source: Architecture Feasibility Finding FEAS-008
- Added: 2026-11-18

**FR-015:** The system SHALL emit a structured JSON response containing total platforms, success count, failure count, and a detailed array of per-platform results including status, public URL, date, time, and error.
- Priority: High
- Source: Practical Test Section 3.B
- Added: 2026-11-18

**FR-016:** The system SHALL expose a `GET /health` liveness probe and `GET /ready` readiness probe returning HTTP 200.
- Priority: Medium
- Source: SRE Architecture ISSUE-012
- Added: 2026-11-18

---

### 3.2 Non-Functional Requirements

**NFR-001:** The system SHALL complete concurrent execution across all 5 platforms within a maximum turnaround time of 10.0 seconds.
- Category: Performance & Latency
- Source: Architecture Invariant INV-006
- Added: 2026-11-18

**NFR-002:** The system SHALL achieve an automated test coverage of at least 90% across services, validators, and adapters.
- Category: Quality & Maintainability
- Source: ISO/IEC/IEEE 29119 Test Standards
- Added: 2026-11-18

**NFR-003:** The system SHALL redact sensitive authentication tokens (`Bearer ***REDACTED***`) from all application log streams.
- Category: Security & Privacy
- Source: OWASP ASVS v4.0 & PCI-DSS Log Sanitization Standards
- Added: 2026-11-18

**NFR-004:** The system SHALL prevent Server-Side Request Forgery (SSRF) by treating the CTA URL purely as published text content without issuing outbound fetches to internal IP ranges.
- Category: Security & Ingress Hardening
- Source: OWASP API Security Top 10 API7:2023
- Added: 2026-11-18

**NFR-005:** The system SHALL maintain a clean layered architecture with unidirectional dependencies: Router $\to$ Validator $\to$ Service $\to$ Adapters.
- Category: Architecture Conformance
- Source: Clean Architecture Domain Boundary Standards
- Added: 2026-11-18

**NFR-006:** The system SHALL be packaged as a lightweight, multi-stage Docker container executing as a non-root user (`appuser`).
- Category: Deployment & DevOps
- Source: Twelve-Factor App Configuration Spec
- Added: 2026-11-18

---

## 4. Acceptance Criteria

**AC-FR-001:** Given a running server, when a client issues an HTTP POST to `/posting` with a valid JSON payload, then the system processes the request and responds with HTTP 200.

**AC-FR-002:** Given an incoming request with a message of 201 characters, when validation runs, then the system immediately returns HTTP 422 with a detail message indicating character limit violation.

**AC-FR-003:** Given an incoming request with 0 URLs or 2 URLs, when validation runs, then the system returns HTTP 422 with a detail message indicating exactly one CTA URL is required.

**AC-FR-004:** Given a message containing `Check this out (https://example.com).`, when extraction runs, then the extracted URL is cleaned to `https://example.com` without trailing parenthesis or period.

**AC-FR-005:** Given a valid request, when the service layer executes, then posting tasks for LinkedIn, Dev.to, Hashnode, Mastodon, and Telegram are all initiated.

**AC-FR-006:** Given valid LinkedIn credentials, when the LinkedIn adapter executes, then a POST request is sent to `https://api.linkedin.com/v2/ugcPosts` and the published update URL is returned.

**AC-FR-007:** Given valid Dev.to credentials, when the Dev.to adapter executes, then an article payload containing synthesized title and markdown body is sent to `https://dev.to/api/articles`.

**AC-FR-008:** Given valid Hashnode credentials, when the Hashnode adapter executes, then a GraphQL mutation containing title, contentMarkdown, and publicationId is sent to `https://gql.hashnode.com`.

**AC-FR-009:** Given valid Mastodon credentials, when the Mastodon adapter executes, then a status POST is sent to `{MASTODON_BASE_URL}/api/v1/statuses` and the status URL is returned.

**AC-FR-010:** Given valid Telegram credentials, when the Telegram adapter executes, then a message POST is sent to `https://api.telegram.org/bot{TOKEN}/sendMessage` targeting `@channel_username`.

**AC-FR-011:** Given 5 platform adapters with simulated 1-second network latency each, when the posting service runs, then total elapsed time is $\le 2.0$ seconds (proving parallel execution, not 5.0 seconds sequential).

**AC-FR-012:** Given one adapter returning an HTTP 500 error, when the posting service runs, then that adapter reports `status: "failed"` while the remaining 4 adapters report `status: "success"`.

**AC-FR-013:** Given an adapter whose response is delayed by 10.0 seconds, when execution reaches 8.0 seconds, then `asyncio.wait_for` terminates the task and reports `status: "failed", error: "Platform timeout after 8s"`.

**AC-FR-014:** Given an adapter receiving an HTTP 429 response with header `Retry-After: 30`, then the result captures `error: "Rate limit exceeded. Retry after 30s"`.

**AC-FR-015:** Given any valid request execution, then the response body strictly adheres to the schema: `{ "success": boolean, "total_platforms": int, "successful_posts": int, "failed_posts": int, "results": [ ... ] }`.

**AC-FR-016:** Given a running service, when a client issues an HTTP GET to `/health`, then the system responds immediately with HTTP 200 `{ "status": "ok" }`.

---

## 5. Out of Scope
- Scheduling future or recurring posts via background queues (Celery/RabbitMQ).
- Multi-user authentication, JWT user registration, or database tenancy models.
- Uploading binary media attachments (images, video clips, audio).
- Automated interactive OAuth consent flows (tokens are provisioned via environment variables).

---

## 6. Change Log

| Date | Version | Task | Change Summary | Status |
|---|---|---|---|---|
| 2026-11-18 | 1.0.0 | Initial Blueprint Documentation | Formal IEEE 830 SRS creation covering FR-001 through FR-016, NFR-001 through NFR-006, and Acceptance Criteria | ✅ Done |
