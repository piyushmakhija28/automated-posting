# Level 6: Testing Strategy & Test Suites — 3-Tier Test Cases Catalog

**Document ID:** `DOC-TST-02-TEST-CATALOG`  
**Project:** `automated-posting`  
**Author:** Principal Software Architect
**Reviewer:** Staff Backend Engineering Lead
**Status:** APPROVED  
**Standard:** Triad Testing Specification (Positive, Negative, Boundary)

---

## 1. Positive Testing Suite (Happy Path Scenarios)

| Test ID | Test Category | Input Payload / Pre-conditions | Expected Behavior | Assertions |
|---|---|---|---|---|
| **TC-POS-01** | Happy Path Fan-Out | Standard valid message (120 chars) with valid HTTPS link; all 5 mock adapters configured. | Concurrently posts to 5 platforms; returns HTTP 200. | `status_code == 200`, `total_platforms == 5`, `successful_posts == 5`, `failed_posts == 0`. |
| **TC-POS-02** | Exact Boundary Max Length | Message of exactly 200 characters including link. | Accepted by validator; posts to platforms. | `status_code == 200`, `response.json()["success"] is True`. |
| **TC-POS-03** | Minimum Length Valid Link | Minimal valid message: `"Check https://a.co"` (17 chars). | Accepted by validator; posts to platforms. | `status_code == 200`. |
| **TC-POS-04** | Complex Query Parameters | URL with query parameters: `"Promo https://dxora.com/blog?ref=twitter&campaign=winter2026"`. | Cleanly extracted and dispatched to external APIs without mangling query string. | `posted_url` contains full query parameters intact. |
| **TC-POS-05** | Health & Readiness | HTTP GET to `/health` and `/ready`. | Returns HTTP 200 immediately. | `status_code == 200`, `json() == {"status": "ok"}`. |

---

## 2. Negative Testing Suite (Error & Fault Scenarios)

| Test ID | Test Category | Input Payload / Pre-conditions | Expected Behavior | Assertions |
|---|---|---|---|---|
| **TC-NEG-01** | Character Limit Exceeded | Message of 201 characters containing 1 URL. | Rejected at validator before any network call. | `status_code == 422`, `detail[0]["msg"]` contains `"exceeds maximum allowed limit of 200"`. |
| **TC-NEG-02** | Missing CTA Link | Message: `"Check out our brand new business platform and scale your online visibility!"` (0 URLs). | Rejected by Pydantic validator. | `status_code == 422`, `detail[0]["msg"]` contains `"Message must contain exactly one valid CTA URL"`. |
| **TC-NEG-03** | Multiple CTA Links | Message: `"Visit https://site-a.com and also check https://site-b.com for updates!"` (2 URLs). | Rejected by Pydantic validator. | `status_code == 422`, `detail[0]["msg"]` contains `"Message contains 2 URLs. Exactly one CTA URL is permitted"`. |
| **TC-NEG-04** | Empty String Message | Message: `""` or whitespace `"   "`. | Rejected by Pydantic validator. | `status_code == 422`, `type == "string_too_short"`. |
| **TC-NEG-05** | Malformed Protocol | Message: `"Explore ftp://files.dxora.com/data"`. | Rejected by Pydantic validator (only `http` or `https` permitted). | `status_code == 422`. |
| **TC-NEG-06** | Bare Domain Without Schema | Message: `"Explore dxora.com for details"`. | Rejected by validator (regex requires `http://` or `https://`). | `status_code == 422`, `"0 URLs found"`. |
| **TC-NEG-07** | Non-JSON Payload | Raw text or corrupted binary body sent with `Content-Type: application/json`. | FastAPI ingress parser rejects. | `status_code == 422`. |
| **TC-NEG-08** | Missing Required Field | Request body `{ "text": "hello https://dxora.com" }` (missing `message`). | Pydantic validation rejects missing required field. | `status_code == 422`, `loc == ["body", "message"]`. |

---

## 3. Edge-Case Testing Suite (Boundary & Edge Scenarios)

| Test ID | Test Category | Input Payload / Pre-conditions | Expected Behavior | Assertions |
|---|---|---|---|---|
| **TC-EDG-01** | URL in Parentheses | Message: `"Read the monograph (https://dxora.com/paper) today!"` | Regex extracts URL and strips trailing `)`. | Extracted URL is `https://dxora.com/paper` (not `...paper)`). |
| **TC-EDG-02** | URL with Trailing Punctuation | Message: `"Visit our launch page: https://dxora.com/launch."` | Regex strips trailing period `.`. | Extracted URL is `https://dxora.com/launch`. |
| **TC-EDG-03** | Unicode & Emojis | Message: `"🚀 Scale your cloud modern AI workflows! 🔥 https://dxora.com 🌟"` | Characters counted properly by Python unicode codepoint metrics. | Posts successfully, emojis preserved in downstream payloads. |
| **TC-EDG-04** | Upstream 401 Unauthorized | LinkedIn returns HTTP 401 (token expired); others succeed. | LinkedIn reports `failed` with diagnostic; others report `success`; overall HTTP 200. | `status_code == 200`, `successful_posts == 4`, `failed_posts == 1`, LinkedIn error matches token expired. |
| **TC-EDG-05** | Upstream 429 Rate Limit | Mastodon returns HTTP 429 with `Retry-After: 60`. | Captured gracefully; does not crash; error contains rate limit diagnosis. | Mastodon result has `status == "failed"`, `error` contains `"Rate limit exceeded"`. |
| **TC-EDG-06** | Upstream 500 Server Error | Dev.to returns HTTP 500 Internal Server Error. | Captured gracefully; does not crash; other 4 succeed. | Dev.to result has `status == "failed"`, others `status == "success"`. |
| **TC-EDG-07** | Network Socket Timeout (>8s) | Telegram adapter simulated to sleep for 10 seconds. | Terminated after 8.0s by `asyncio.wait_for`. | Telegram result has `error == "Platform timeout after 8.0s"`, total time $\approx 8.1\text{s}$. |
| **TC-EDG-08** | All 5 Platforms Fail | All 5 mock transports return HTTP 500 simultaneously. | Returns HTTP 200; `success == false`; all 5 results detailed with errors. | `status_code == 200`, `successful_posts == 0`, `failed_posts == 5`. |
| **TC-EDG-09** | Log Scrubbing Verification | Execution triggers logging with mock token `"Bearer AQV123456789"`. | Log filter masks token in output stream. | Log stream contains `"Bearer ***REDACTED***"`, zero cleartext tokens. |
| **TC-EDG-10** | Unconfigured Environment | Target platform has empty credentials (`None`). | Adapter reports `failed` without making network call. | Result has `error == "Platform credentials not configured in environment variables."`. |
