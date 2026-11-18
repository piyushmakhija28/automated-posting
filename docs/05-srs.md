# Level 0/1: System Requirements Traceability Matrix

**Document ID:** `DOC-05-SRS`  
**Project:** `automated-posting`  
**Author:** Principal Software Architect
**Reviewer:** Staff Backend Engineering Lead
**Status:** APPROVED  
**Standard:** IEEE 830, ISO/IEC/IEEE 29148

---

## 1. Traceability Architecture
This document provides bidirectional traceability linking:
1. Practical Test Specifications
2. Functional Requirements (FR) & Non-Functional Requirements (NFR)
3. Code Modules & Python Classes
4. Architectural Mitigations (Architecture Feasibility Findings)
5. Automated Test Cases

---

## 2. Requirements Traceability Matrix

| Requirement ID | Requirement Summary | Implementation Module | Implementing Class / Function | Architectural Mitigation | Verification Test ID |
|---|---|---|---|---|---|
| **FR-001** | `POST /posting` endpoint | `app/main.py` | `broadcast_message()` | Clean layered routing | `test_post_message_success` |
| **FR-002** | $\le 200$ character length | `app/schemas.py`, `app/utils/validators.py` | `PostRequest.validate_single_cta_url` | INV-001 length bounding | `test_post_message_too_long` |
| **FR-003** | Exactly 1 CTA URL | `app/schemas.py`, `app/utils/validators.py` | `extract_and_validate_url()` | ISSUE-007 regex extraction | `test_post_message_no_url`, `test_post_message_multiple_urls` |
| **FR-004** | URL syntax & sanitation | `app/utils/validators.py` | `clean_url()`, `is_valid_url()` | ISSUE-007 punctuation strip | `test_clean_url_edge_cases` |
| **FR-005** | Autonomous platform routing | `app/services/posting_service.py` | `PostingService.post_to_all()` | INV-003 internal selection | `test_post_message_success` |
| **FR-006** | LinkedIn UGC integration | `app/platforms/linkedin.py` | `LinkedInPlatform.post()` | ISSUE-001 OAuth 2.0 flow | `test_linkedin_adapter_success`, `test_linkedin_adapter_token_expired` |
| **FR-007** | Dev.to article integration | `app/platforms/devto.py` | `DevToPlatform.post()` | ISSUE-002 Title synthesis | `test_devto_adapter_success`, `test_devto_adapter_error` |
| **FR-008** | Hashnode GraphQL integration| `app/platforms/hashnode.py` | `HashnodePlatform.post()` | ISSUE-003 GraphQL mutation | `test_hashnode_adapter_success`, `test_hashnode_adapter_error` |
| **FR-009** | Mastodon statuses integration| `app/platforms/mastodon.py` | `MastodonPlatform.post()` | ISSUE-011 Base URL config | `test_mastodon_adapter_success`, `test_mastodon_adapter_error` |
| **FR-010** | Telegram channel integration | `app/platforms/telegram.py` | `TelegramPlatform.post()` | ISSUE-006 Bot admin check | `test_telegram_adapter_success`, `test_telegram_adapter_not_admin` |
| **FR-011** | Async parallel fan-out | `app/services/posting_service.py` | `asyncio.gather()` in `post_to_all` | ISSUE-004 Non-blocking I/O | `test_parallel_execution_latency` |
| **FR-012** | Bulkhead fault isolation | `app/services/posting_service.py` | `_safe_post()` wrapper | INV-004 Failure containment | `test_partial_failure_isolation` |
| **FR-013** | Per-adapter 8.0s timeout | `app/services/posting_service.py` | `asyncio.wait_for(timeout=8.0)` | ISSUE-005 Timeout cascade | `test_adapter_timeout_handling` |
| **FR-014** | Rate limit detection | `app/platforms/base.py` | `handle_http_error()` | ISSUE-008 429 Retry-After | `test_rate_limit_interception` |
| **FR-015** | Structured response payload | `app/schemas.py` | `PostResponse`, `PlatformResult` | Uniform API wrapper | `test_response_schema_conformance` |
| **FR-016** | Health & readiness probes | `app/main.py` | `get_health()`, `get_ready()` | ISSUE-012 SRE keepalive | `test_health_and_ready_probes` |
| **NFR-001** | Latency SLA $\le 10.0$s | `app/services/posting_service.py` | Concurrent event loop scheduling | High-efficiency async client | `test_sla_conformance` |
| **NFR-002** | $\ge 90\%$ test coverage | `tests/` test suite | Pytest test execution | Strict ISO 29119 test coverage standard | `pytest --cov=app` |
| **NFR-003** | Zero credentials in logs | `app/utils/logger.py` | `SensitiveDataFilter` | ISSUE-009 Token scrubbing | `test_logger_redaction` |
| **NFR-004** | SSRF prevention | `app/utils/validators.py` | Zero outbound fetching of CTA URL | OWASP API7:2023 compliance | `test_ssrf_safety_assertion` |
| **NFR-005** | Clean Architecture | `app/` package structure | Unidirectional dependency graph | Clean Architecture domain separation | Architectural conformance check |
| **NFR-006** | Hardened container | `Dockerfile` | Multi-stage build (`python:3.11-slim`) | CIS Docker & Twelve-Factor standard | Container build & run test |
