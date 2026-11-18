# Level 9: Agile Governance & Management — Master Traceability Matrix

**Document ID:** `DOC-MGT-03-TRACEABILITY`  
**Project:** `automated-posting`  
**Author:** Principal Software Architect & Staff Systems Engineer  
**Status:** APPROVED & SYNCHRONIZED  
**Standard:** ISO/IEC/IEEE 15288 Verification and Validation, IEEE 830 Traceability, GitHub Agile Governance  

---

## 1. Master End-to-End Traceability Matrix

This matrix establishes complete, unbroken forward and backward traceability across requirements, architecture blueprints, concrete target files, test suites, and GitHub sprint issues:

| Practical Test Requirement | PRD FR ID | SRS ID | HLD / LLD Component | Target File(s) | GitHub Sprint Issue | Verification Test ID |
|---|---|---|---|---|:---:|---|
| Single endpoint `POST /posting` | FR-001 | FR-001 | Ingress Router Controller | `app/routers/posting.py` | [#6](https://github.com/piyushmakhija28/automated-posting/issues/6) | `test_router_posting.py::test_post_success` |
| Max 200 characters validation | FR-002 | FR-002 | Ingress PostingForm (Stage 3) | `app/models/forms/posting_form.py` | [#2](https://github.com/piyushmakhija28/automated-posting/issues/2) | `test_validation_pipeline.py::test_char_limit` |
| Exactly one CTA link required | FR-003 | FR-003 | Ingress Regex Extractor (Stage 4) | `app/models/forms/posting_form.py` | [#2](https://github.com/piyushmakhija28/automated-posting/issues/2) | `test_validation_pipeline.py::test_single_cta` |
| URL format validation & strip | FR-004 | FR-004 | Syntax Sanitizer & NFKC (Stage 2) | `app/models/forms/posting_form.py` | [#2](https://github.com/piyushmakhija28/automated-posting/issues/2) | `test_validation_pipeline.py::test_clean_url` |
| Internal platform selection | FR-005 | FR-005 | Autonomous Service Registry | `app/platforms/registry.py` | [#3](https://github.com/piyushmakhija28/automated-posting/issues/3) | `test_adapters.py::test_registry_discovery` |
| Platform 1: LinkedIn integration | FR-006 | FR-006 | `LinkedInAdapter` (UGC Post API) | `app/platforms/linkedin.py` | [#8](https://github.com/piyushmakhija28/automated-posting/issues/8) | `test_adapters.py::test_linkedin_adapter` |
| Platform 2: Dev.to integration | FR-007 | FR-007 | `DevToAdapter` (Forem Articles) | `app/platforms/devto.py` | [#9](https://github.com/piyushmakhija28/automated-posting/issues/9) | `test_adapters.py::test_devto_adapter` |
| Platform 3: Hashnode integration | FR-008 | FR-008 | `HashnodeAdapter` (GraphQL API) | `app/platforms/hashnode.py` | [#10](https://github.com/piyushmakhija28/automated-posting/issues/10) | `test_adapters.py::test_hashnode_adapter` |
| Platform 4: Mastodon integration | FR-009 | FR-009 | `MastodonAdapter` (Statuses API) | `app/platforms/mastodon.py` | [#11](https://github.com/piyushmakhija28/automated-posting/issues/11) | `test_adapters.py::test_mastodon_adapter` |
| Platform 5: Telegram integration | FR-010 | FR-010 | `TelegramAdapter` (Bot sendMessage) | `app/platforms/telegram.py` | [#12](https://github.com/piyushmakhija28/automated-posting/issues/12) | `test_adapters.py::test_telegram_adapter` |
| Parallel async execution | FR-011 | FR-011 | Bulkhead `asyncio.gather` Fan-Out | `app/services/posting_service.py` | [#5](https://github.com/piyushmakhija28/automated-posting/issues/5) | `test_service_posting.py::test_parallel_fanout` |
| Failure isolation (1 fail != all) | FR-012 | FR-012 | `_safe_execute` Try/Catch Boundary | `app/services/posting_service.py` | [#5](https://github.com/piyushmakhija28/automated-posting/issues/5) | `test_resilience_bulkhead.py::test_partial_failure` |
| Per-adapter 3.0s timeout SLA | FR-013 | FR-013 | `asyncio.wait_for` SLA Guard | `app/services/posting_service.py` | [#5](https://github.com/piyushmakhija28/automated-posting/issues/5) | `test_resilience_bulkhead.py::test_adapter_timeout` |
| Rate limiting detection (429) | FR-014 | FR-014 | `_handle_error` Upstream Normalizer | `app/platforms/base.py` | [#3](https://github.com/piyushmakhija28/automated-posting/issues/3) | `test_adapters.py::test_rate_limit_interception` |
| Structured response JSON | FR-015 | FR-015 | `PostingResponseDto` & DTO Helper | `app/models/dtos/posting_dto.py` | [#5](https://github.com/piyushmakhija28/automated-posting/issues/5) | `test_service_posting.py::test_response_schema` |
| Liveness and Readiness probes | FR-016 | FR-016 | SRE Health Probes (`/health`, `/ready`) | `app/routers/health.py` | [#6](https://github.com/piyushmakhija28/automated-posting/issues/6) | `test_router_health.py::test_probes` |
| 7-Stage Input Sanitization | FR-017 | FR-017 | NFKC, BOM, Zero-Width, Bidi Rejection | `app/models/forms/posting_form.py` | [#2](https://github.com/piyushmakhija28/automated-posting/issues/2) | `test_validation_pipeline.py::test_sanitization` |
| SSRF & Hostname Threat Defense | FR-018 | FR-018 | RFC 1918 Private IP & Loopback Filter | `app/models/forms/posting_form.py` | [#2](https://github.com/piyushmakhija28/automated-posting/issues/2) | `test_validation_pipeline.py::test_ssrf_filter` |
| Adapter Factory & Discovery | LLD-05 | LLD-05 | `AdapterRegistry` Factory Pattern | `app/platforms/registry.py` | [#3](https://github.com/piyushmakhija28/automated-posting/issues/3) | `test_adapters.py::test_registry_factory` |
| Domain Exception Hierarchy | LLD-06 | LLD-06 | `ApplicationException` & RFC 7807 | `app/core/exceptions.py` | [#2](https://github.com/piyushmakhija28/automated-posting/issues/2) | `test_router_posting.py::test_rfc7807_mapping` |
| Centralized Typed Constants | LLD-07 | LLD-07 | 4 Dedicated Constant Classes | `app/core/constants.py` | [#2](https://github.com/piyushmakhija28/automated-posting/issues/2) | `test_validation_pipeline.py::test_constants` |
| Zero Secrets in Logs | NFR-003 | NFR-003 | `SensitiveDataFilter` Logger Filter | `app/core/logging.py` | [#2](https://github.com/piyushmakhija28/automated-posting/issues/2) | `test_validation_pipeline.py::test_log_masking` |
| $\ge 90\%$ Code Coverage Gate | NFR-002 | NFR-002 | Triad Testing Across 11 Layers | `tests/test_*.py` | [#7](https://github.com/piyushmakhija28/automated-posting/issues/7) | `pytest --cov=app --cov-fail-under=90` |
| Multi-Stage Containerization | NFR-006 | NFR-006 | Multi-Stage Non-Root OCI Image | `Dockerfile` | [#13](https://github.com/piyushmakhija28/automated-posting/issues/13) | Container build & health check test |
| Automated CI/CD Pipeline | NFR-007 | NFR-007 | GitHub Actions CI/CD Workflow | `.github/workflows/ci-cd.yml` | [#14](https://github.com/piyushmakhija28/automated-posting/issues/14) | GitHub Actions CI runner verification |
