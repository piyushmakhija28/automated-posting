# Level 4: Reliability & Fault Tolerance Architecture — Error Catalogue & Graceful Degradation

**Document ID:** `DOC-RES-03-ERROR-CATALOGUE`  
**Project:** `automated-posting`  
**Author:** Principal Software Architect
**Reviewer:** Staff Backend Engineering Lead
**Status:** APPROVED  
**Standard:** RFC 7807 (Problem Details for HTTP APIs), RFC 7807 Problem Details Standard

---

## 1. Error Taxonomy & Classification

The system classifies all potential error conditions into three distinct operational domains:

```
                            [ ERROR DOMAINS ]
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
[ Ingress Errors ]          [ Adapter Errors ]          [ Upstream Errors ]
 (HTTP 422 Client)          (HTTP 200 Itemized)         (HTTP 5xx Server)
  - Message > 200 chars      - Token Expired             - Out of Memory
  - Missing CTA link         - Bot Not Admin             - Python Runtime Crash
  - Multiple CTA links       - Execution Timeout (>8s)   - Unhandled Exception
  - Syntax/Protocol error    - Rate Limited (HTTP 429)
```

---

## 2. Exhaustive Error Catalogue

| Error Code | Error Context | Root Cause | Client Response Code | Diagnostic Message Emitted |
|---|---|---|---|---|
| **ERR-ING-001** | Ingress Validation | Character count $>200$ | `HTTP 422` | `"Message length (N chars) exceeds maximum allowed limit of 200 characters."` |
| **ERR-ING-002** | Ingress Validation | 0 URLs found | `HTTP 422` | `"Message must contain exactly one valid CTA URL (http:// or https://). None found."` |
| **ERR-ING-003** | Ingress Validation | $>1$ URLs found | `HTTP 422` | `"Message contains N URLs. Exactly one CTA URL is permitted."` |
| **ERR-ING-004** | Ingress Validation | URL missing netloc/domain | `HTTP 422` | `"Extracted CTA URL '...' is syntactically invalid."` |
| **ERR-PLT-001** | LinkedIn Adapter | OAuth 2.0 Token Expired (401) | `HTTP 200` (Itemized) | `"LinkedIn OAuth token expired or invalid — refresh token required."` |
| **ERR-PLT-002** | Dev.to Adapter | Invalid API Key (401) | `HTTP 200` (Itemized) | `"Dev.to API error: 401 Unauthorized — verify DEVTO_API_KEY."` |
| **ERR-PLT-003** | Hashnode Adapter | Missing Publication ID (400) | `HTTP 200` (Itemized) | `"Hashnode error: Publication not found or HASHNODE_PUBLICATION_ID invalid."` |
| **ERR-PLT-004** | Telegram Adapter | Bot not channel admin (400) | `HTTP 200` (Itemized) | `"Telegram Bot API error: Chat not found or Bot is not channel administrator."` |
| **ERR-PLT-005** | Mastodon Adapter | Network Connection Error | `HTTP 200` (Itemized) | `"Mastodon connection failed to target instance host."` |
| **ERR-PLT-006** | Any Platform | Coroutine exceeds 8.0s | `HTTP 200` (Itemized) | `"Platform execution timed out after 8.0 seconds."` |
| **ERR-PLT-007** | Any Platform | Rate Limit Triggered (429) | `HTTP 200` (Itemized) | `"Rate limit exceeded. Retry after Ns."` |
| **ERR-CFG-001** | Any Platform | Env variables missing | `HTTP 200` (Itemized) | `"Platform credentials not configured in environment variables."` |

---

## 3. Graceful Degradation Matrix

| Scenario | LinkedIn | Dev.to | Hashnode | Mastodon | Telegram | Overall HTTP Status | `success` Field |
|---|---|---|---|---|---|---|---|
| **Scenario A: All Platforms Up** | ✅ Success | ✅ Success | ✅ Success | ✅ Success | ✅ Success | `HTTP 200` | `true` |
| **Scenario B: 1 Platform Down (Telegram)** | ✅ Success | ✅ Success | ✅ Success | ✅ Success | ❌ Failed | `HTTP 200` | `true` |
| **Scenario C: 3 Platforms Down** | ❌ Failed | ✅ Success | ❌ Failed | ✅ Success | ❌ Failed | `HTTP 200` | `true` |
| **Scenario D: All 5 Platforms Down** | ❌ Failed | ❌ Failed | ❌ Failed | ❌ Failed | ❌ Failed | `HTTP 200` | `false` |
| **Scenario E: Ingress Validation Fail** | ⏸️ Not Run | ⏸️ Not Run | ⏸️ Not Run | ⏸️ Not Run | ⏸️ Not Run | `HTTP 422` | N/A |
