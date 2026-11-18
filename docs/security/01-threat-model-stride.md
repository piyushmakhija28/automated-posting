# Level 3: Security & Threat Modeling Architecture — STRIDE Analysis

**Document ID:** `DOC-SEC-01-STRIDE`  
**Project:** `automated-posting`  
**Author:** Principal Software Architect
**Reviewer:** Staff Backend Engineering Lead
**Status:** APPROVED  
**Standard:** Microsoft STRIDE Threat Modeling Methodology, OWASP Security by Design

---

## 1. Threat Modeling Scope & Trust Boundaries

The system architecture exposes two primary trust boundaries:
1. **Trust Boundary 1 (Ingress):** Between external untrusted API clients and our FastAPI ingress endpoint (`POST /posting`).
2. **Trust Boundary 2 (Egress):** Between our application server and remote third-party platform API gateways (LinkedIn, Dev.to, Hashnode, Mastodon, Telegram).

```
[ Untrusted Client ] ──(Boundary 1: Ingress)──► [ FastAPI Ingress Engine ] ──(Boundary 2: Egress)──► [ Third-Party APIs ]
```

---

## 2. STRIDE Threat Matrix & Mitigations

| Threat Category | Potential Attack Vector | Severity | System Architectural Mitigation |
|---|---|---|---|
| **S — Spoofing** | An attacker attempts to forge platform API credentials or impersonate the publisher. | High | 12-Factor credential isolation: tokens never accepted from client payloads; tokens loaded exclusively from server environment variables. |
| **T — Tampering** | An attacker submits malicious payloads containing SQL injection, shell metacharacters, or corrupted unicode strings. | Medium | Pydantic v2 strict typing rejects non-string types; payload treated strictly as inert string buffers; no dynamic query or shell evaluation. |
| **R — Repudiation** | An author claims they did not publish an offensive post, or the system cannot prove where a failure occurred. | Medium | Structured JSON logging generates unique `X-Request-ID` tracing each request from ingress to egress, recording timestamps and response status codes. |
| **I — Information Disclosure** | Authorization tokens or internal server error stack traces are leaked via response bodies or logging outputs. | Critical | Custom `SanitizedLogger` masks all Bearer tokens (`***REDACTED***`). FastAPI unhandled exception middleware suppresses internal tracebacks. |
| **D — Denial of Service** | An attacker submits multi-megabyte payloads, or slow third-party servers exhaust server connection pools. | High | Ingress payload bounded at 200 chars; per-adapter timeouts capped at 8.0s; connection pooling with max connection limits via `httpx.AsyncClient`. |
| **E — Elevation of Privilege** | An attacker attempts to exploit vulnerabilities in containerized runtime to gain host root access. | High | Docker container executes as non-root user (`appuser` with UID 10001) with read-only root filesystem capabilities where supported. |

---

## 3. Server-Side Request Forgery (SSRF) Defense Architecture

### The Threat:
In applications that process URLs, a frequent critical vulnerability is **SSRF (CWE-918)**: an attacker submits a URL pointing to internal private network addresses (e.g. `http://169.254.169.254/latest/meta-data/` to steal AWS cloud instance credentials, or `http://localhost:8080/admin`). If the backend server attempts to fetch the URL content, private infrastructure is compromised.

### The Architectural Invariant:
**The Automated Multi-Platform Posting Engine NEVER issues an HTTP GET, HEAD, or POST to the user-supplied CTA URL.**
- The CTA URL is extracted via regular expressions strictly to validate that a link is present.
- The URL is embedded as **plain text / string metadata** inside the JSON payload forwarded to LinkedIn, Dev.to, Hashnode, Mastodon, and Telegram.
- Third-party platform servers (e.g., LinkedIn's link crawler) may optionally crawl the public link to generate OpenGraph link previews, but our host server is completely insulated from SSRF vectors.
