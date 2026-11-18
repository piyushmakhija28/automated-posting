# Level 0: Product Requirements Document (PRD)

**Document ID:** `DOC-01-PRD`  
**Project:** `automated-posting`  
**Author:** Principal Software Architect
**Reviewer:** Staff Backend Engineering Lead
**Approver:** Technical Architecture Board
**Version:** 1.0.0 | **Date:** 2026-11-18  
**Standards:** IEEE 830, ISO/IEC/IEEE 29148, `rules/11-documentation-files.md`

---

## 1. Executive Summary
The **Automated Multi-Platform Posting Engine** is an enterprise-grade microservice engineered with **FastAPI** that eliminates the manual burden of syndicating short promotional announcements across multiple developer, social, and messaging channels. By accepting a single validated payload, the engine autonomously adapts, authenticates, and dispatches the message concurrently across 5 distinct third-party platforms.

---

## 2. Target Personas & Stakeholders

| Persona | Role | Primary Objective | Key Pain Point |
|---|---|---|---|
| **P-1: DevRel / Tech Evangelist** | Developer Relations Engineer | Announce open-source releases, blogs, and demos across Dev.to, Hashnode, LinkedIn, and Telegram simultaneously. | Manually re-formatting and re-posting across 5 portals consumes 30+ minutes per release. |
| **P-2: Growth Marketing Lead** | Digital Marketing Specialist | Broadcast campaign promotions with tracking CTA links across social channels. | Inconsistent character limits, auth failures, and rate limits break marketing workflows. |
| **P-3: Platform API Consumer** | Internal Microservice / CI/CD Bot | Programmatically trigger broadcast notifications upon deployment completion. | Requires predictable HTTP status codes, structured JSON error breakdowns, and sub-10s latency. |

---

## 3. Product Vision & Success Metrics (OKRs)

- **Objective:** Provide a bulletproof, zero-maintenance broadcasting API capable of concurrent syndication with graceful degradation.
- **Key Result 1:** $100\%$ fault isolation — zero single points of failure across platform adapters.
- **Key Result 2:** Sub-8 second end-to-end response time for all 5 platforms combined under normal network conditions.
- **Key Result 3:** $\ge 90\%$ automated test coverage enforcing positive, negative, and edge-case invariants.
- **Key Result 4:** Zero security vulnerabilities reported under OWASP API Top 10 guidelines and zero credential leaks in logs.

---

## 4. Functional Requirements (FR)

| FR ID | Requirement Title | Detailed Specification | WSJF Priority | Kano Model | Linked Issue |
|---|---|---|---|---|---|
| **FR-001** | Ingress API Endpoint | Expose `POST /posting` listening on port 4000 (configurable via `APP_PORT`). Accept `application/json` payload containing string attribute `message`. | High (WSJF: 18) | Must-Be | — |
| **FR-002** | Message Length Validation | Reject any message string exceeding 200 unicode characters with HTTP 422 Unprocessable Entity. | High (WSJF: 20) | Must-Be | INV-001 |
| **FR-003** | CTA URL Extraction & Count | Validate that the message contains **exactly one** valid HTTP/HTTPS URL. Reject messages with 0 URLs or $>1$ URLs with HTTP 422. | High (WSJF: 20) | Must-Be | ISSUE-007 |
| **FR-004** | URL Syntax & Sanitization | Clean extracted URLs by trimming trailing punctuation (`.,;:!?)'`). Assert valid protocol (`http://` or `https://`). Reject bare domains (`example.com`). | Medium (WSJF: 15) | Must-Be | ISSUE-007 |
| **FR-005** | Autonomous Platform Selection | Automatically route the payload to all 5 integrated platforms without requiring client configuration. | High (WSJF: 19) | Must-Be | INV-003 |
| **FR-006** | LinkedIn Adapter Integration | Publish message to LinkedIn Feed via official UGC Posts API using OAuth 2.0 User Access Token. | High (WSJF: 17) | One-Dimensional | ISSUE-001 |
| **FR-007** | Dev.to Adapter Integration | Synthesize article title from the first 60 chars; wrap full message as markdown body; publish via Dev.to REST API. | High (WSJF: 17) | One-Dimensional | ISSUE-002 |
| **FR-008** | Hashnode Adapter Integration | Execute GraphQL `publishPost` mutation against `https://gql.hashnode.com` utilizing `publicationId` and personal access token. | High (WSJF: 17) | One-Dimensional | ISSUE-003 |
| **FR-009** | Mastodon Adapter Integration | Publish status to target Mastodon instance (default: `mastodon.social`) via REST statuses API using Bearer Token. | High (WSJF: 16) | One-Dimensional | ISSUE-011 |
| **FR-010** | Telegram Adapter Integration | Dispatch message with CTA to configured public channel username (`@channel`) via Telegram Bot API `sendMessage`. | High (WSJF: 16) | One-Dimensional | ISSUE-006 |
| **FR-011** | Parallel Non-Blocking Execution | Execute all 5 platform dispatches concurrently using `asyncio.gather(..., return_exceptions=True)`. Zero synchronous network blocking. | High (WSJF: 20) | Must-Be | ISSUE-004 |
| **FR-012** | Bulkhead Fault Isolation | Isolate adapter failures. If platform $X$ fails or times out, platforms $Y$ and $Z$ must complete normally. | High (WSJF: 20) | Must-Be | ISSUE-005 |
| **FR-013** | Granular Adapter Timeouts | Enforce an 8.0-second timeout per adapter via `asyncio.wait_for`. Return `status: "failed"` with timeout diagnosis upon breach. | High (WSJF: 18) | Must-Be | ISSUE-005 |
| **FR-014** | Rate Limit Interception | Detect HTTP 429 status codes; parse `Retry-After` if present; return informative error without crashing. | Medium (WSJF: 14) | Attractive | ISSUE-008 |
| **FR-015** | Unified Response Telemetry | Return structured JSON with top-level summary counts and typed array of platform outcomes with localized timestamps. | High (WSJF: 19) | Must-Be | — |
| **FR-016** | Ingress Input Sanitization | Strip zero-width Unicode characters, normalize text via NFKC, and reject Trojan Source bidirectional override characters (`\u202A`–`\u202E`) and null bytes (`\x00`). | High (WSJF: 19) | Must-Be | DOC-SEC-04 |
| **FR-017** | SSRF & Hostname Threat Defense | Screen extracted CTA URL against loopback (`localhost`, `127.0.0.1`), RFC 1918 private subnets, cloud metadata (`169.254.169.254`), and prohibited internal ports (22, 25, 3306, 5432, 6379). | High (WSJF: 19) | Must-Be | DOC-SEC-04 |

---

## 5. Non-Functional Requirements (NFR)

| NFR ID | Category | Metric / Specification | Verification Method |
|---|---|---|---|
| **NFR-001** | **Latency & SLA** | Total API turnaround $\le 10.0$ seconds for full fan-out execution under normal latency. | Automated latency integration tests (`pytest`). |
| **NFR-002** | **Availability & Resiliency** | System returns HTTP 200 as long as input validation succeeds, even if all 5 platforms fail upstream. | Unit test with 5 simulated 500 errors. |
| **NFR-003** | **Security: Credential Safety** | Zero API keys, passwords, or tokens hardcoded in repository or emitted in log streams. | Pre-commit git scan + `SanitizedLogger` automated unit test. |
| **NFR-004** | **Security: SSRF Prevention** | CTA URL is passed strictly as message text to external APIs; the engine NEVER fetches internal or local IP addresses (`127.0.0.1`, `169.254.169.254`). | Code audit + adversarial test cases. |
| **NFR-005** | **Maintainability: Clean Arch** | Layered architecture enforcing unidirectional dependencies: Router $\to$ Validator $\to$ Service $\to$ Adapters. | Static analysis via `architecture-conformance-auditor`. |
| **NFR-006** | **Compatibility: Modern Typing** | Full type hinting using Python 3.10+ syntax (`X \| Y`, `list[T]`) and Pydantic v2. | `mypy --strict` compliance. |
| **NFR-007** | **Observability: Telemetry** | Structured JSON log output with correlation IDs (`X-Request-ID`) attached to every request lifespan. | Inspection of standard error log formatting. |
| **NFR-008** | **Observability: Probes** | Dedicated `/health` (liveness) and `/ready` (readiness) endpoints returning HTTP 200. | Automated curl / pytest probe assertion. |
| **NFR-009** | **Container Portability** | Containerized execution via multi-stage Dockerfile operating as non-root user (`appuser`). | Docker build & container execution validation. |
| **NFR-010** | **Test Quality Gate** | Combined automated test coverage $\ge 90\%$ across all core modules. | `pytest --cov=app --cov-fail-under=90`. |

---

## 6. Data & Payload Contracts

### 6.1 Request Contract (`POST /posting`)
```json
{
  "message": "Discover cutting-edge microservices and automated publishing pipelines! https://techdeveloper.io"
}
```

### 6.2 Response Contract (`HTTP 200 OK`)
```json
{
  "success": true,
  "total_platforms": 5,
  "successful_posts": 4,
  "failed_posts": 1,
  "results": [
    {
      "platform": "LinkedIn",
      "status": "success",
      "posted_url": "https://www.linkedin.com/feed/update/urn:li:share:7123456789",
      "public_access": true,
      "date": "2026-11-18",
      "time": "12:30:15",
      "error": null
    },
    {
      "platform": "Dev.to",
      "status": "success",
      "posted_url": "https://dev.to/piyush/discover-cutting-edge-microservices-abc123",
      "public_access": true,
      "date": "2026-11-18",
      "time": "12:30:16",
      "error": null
    },
    {
      "platform": "Hashnode",
      "status": "success",
      "posted_url": "https://hashnode.com/post/abc123xyz",
      "public_access": true,
      "date": "2026-11-18",
      "time": "12:30:16",
      "error": null
    },
    {
      "platform": "Mastodon",
      "status": "success",
      "posted_url": "https://mastodon.social/@piyush/11234567890",
      "public_access": true,
      "date": "2026-11-18",
      "time": "12:30:17",
      "error": null
    },
    {
      "platform": "Telegram",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Telegram Bot API error: Chat not found or Bot is not channel administrator"
    }
  ]
}
```

### 6.3 Validation Error Contract (`HTTP 422 Unprocessable Entity`)
```json
{
  "detail": [
    {
      "loc": ["body", "message"],
      "msg": "Message contains 2 URLs. Exactly 1 CTA URL is required.",
      "type": "value_error"
    }
  ]
}
```

---

## 7. User Stories (INVEST Model)

- **US-001 (Happy Path Multi-Broadcast):** As an API client, I want to submit a 180-character announcement with my blog URL, so that it is instantly published across LinkedIn, Dev.to, Hashnode, Mastodon, and Telegram without manual intervention.
- **US-002 (Input Character Boundary Guard):** As an API client, if I submit a message of 201 characters, I want to receive an immediate HTTP 422 error detailing the character limit violation, so that I can trim my copy.
- **US-003 (CTA Link Enforcement):** As an API client, if I omit a CTA URL or include two URLs, I want the system to reject my payload with a clear validation error, so that marketing link integrity is preserved.
- **US-004 (Partial Failure Resilience):** As an API client, if the LinkedIn token has expired, I want the system to publish to the remaining 4 platforms successfully and return a failed status with an explanation for LinkedIn, so that single platform downtime does not block my entire campaign.
- **US-005 (Audit & Observability):** As a DevSecOps engineer, I want all server logs to mask sensitive authorization tokens, so that no external logging aggregator captures credentials in cleartext.

---

## 8. Out of Scope & Future Roadmap
- **v1.1:** Persistent audit database (PostgreSQL) tracking historical broadcast logs.
- **v1.2:** Scheduled / delayed posting via Redis and Celery/Arq workers.
- **v1.3:** Image and rich media attachments alongside text messages.
- **v1.4:** OAuth token auto-refresh loop for LinkedIn refresh tokens.
