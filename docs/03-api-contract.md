# Level 1.5: API Contract & Interface Specification

**Document ID:** `DOC-03-API-CONTRACT`  
**Project:** `automated-posting`  
**Author:** Principal Software Architect
**Reviewer:** Staff Backend Engineering Lead
**Status:** APPROVED  
**Standard:** OpenAPI 3.1.0, RFC 7807 (Problem Details), `rules/26-openapi-documentation.md`

---

## 1. Protocol & Server Specification

- **Protocol:** HTTP/1.1 over TLS (HTTPS in production)
- **Content-Type:** `application/json` (UTF-8 encoding)
- **Local Endpoint:** `http://localhost:4000/posting`
- **Interactive Documentation:**
  - Swagger UI: `http://localhost:4000/docs`
  - ReDoc: `http://localhost:4000/redoc`
  - OpenAPI Spec: `http://localhost:4000/openapi.json`

---

## 2. Endpoint: `POST /posting`

### 2.1 Operation Metadata
- **Summary:** Publish short message and CTA link across 5+ platforms concurrently.
- **Description:** Accepts a validated message (max 200 characters, containing exactly one CTA URL), validates input integrity, and broadcasts the content in parallel to LinkedIn, Dev.to, Hashnode, Mastodon, and Telegram. Returns granular status per platform.
- **Tags:** `Posting`

### 2.2 Request Schema

#### Request Headers:
| Header | Value | Required | Description |
|---|---|---|---|
| `Content-Type` | `application/json` | Yes | Specifies JSON payload. |
| `X-Request-ID` | UUID string | Optional | Correlation ID for distributed log tracing. |

#### Request Body (`application/json`):
```json
{
  "message": "Accelerate your cloud modernization with high-performance publishing pipelines! https://dxora.com"
}
```

#### Field Constraints & Ingress Sanitization Pipeline:
| Attribute | Type | Constraints | Description |
|---|---|---|---|
| `message` | `string` | $\text{min\_length}=1$, $\text{max\_length}=200$ | The broadcast copy. Must contain exactly 1 valid HTTP/HTTPS URL. |

##### Ingress Sanitization Invariants:
1. **BOM & Zero-Width Stripping:** UTF-8 BOM (`\uFEFF`) and zero-width spaces (`\u200B`–`\u200D`) are stripped before length evaluation.
2. **Unicode Normalization:** Normalized to canonical NFKC format (`unicodedata.normalize('NFKC', ...)`).
3. **Trojan Source Defense:** Bidirectional override characters (`\u202A`–`\u202E`, `\u2066`–`\u2069`) and null bytes (`\x00`) trigger immediate rejection (`ERR_MALICIOUS_CONTROL_CHARS`).
4. **URL Boundary Normalization:** Cleanly strips trailing punctuation (`.,;:!?)'"`) and validates strict `http://` or `https://` scheme.
5. **SSRF & Threat Hostname Screening:** Rejects loopback (`localhost`, `127.0.0.1`), RFC 1918 private subnets, cloud metadata IPs (`169.254.169.254`), and dangerous ports (`22, 25, 3306, 5432, 6379`) with `ERR_SSRF_PROHIBITED`.

---

### 2.3 Response Schemas

#### Response: `200 OK` (Standard Execution Telemetry)
Returned when the request is syntactically valid and processed across platforms (even if one or more individual platforms fail upstream).

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
      "posted_url": "https://dev.to/piyush/accelerate-your-cloud-modernization-abc123",
      "public_access": true,
      "date": "2026-11-18",
      "time": "12:30:16",
      "error": null
    },
    {
      "platform": "Hashnode",
      "status": "success",
      "posted_url": "https://hashnode.com/post/xyz789",
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

#### Field Specifications:
| Attribute | Type | Description |
|---|---|---|
| `success` | `boolean` | `true` if at least one platform succeeded or processing completed normally; `false` only if all failed. |
| `total_platforms` | `integer` | Count of target platforms attempted (minimum 5). |
| `successful_posts`| `integer` | Count of platforms reporting `status: "success"`. |
| `failed_posts`    | `integer` | Count of platforms reporting `status: "failed"`. |
| `results`         | `array[PlatformResult]` | Itemized outcome per platform adapter. |
| `results[].platform` | `string` | Human-readable platform name (e.g. `LinkedIn`, `Dev.to`). |
| `results[].status`   | `string` | `success` or `failed`. |
| `results[].posted_url` | `string \| null` | Permanent URL to public post if successful; `null` if failed. |
| `results[].public_access` | `boolean` | `true` if public without login; `false` otherwise. |
| `results[].date` | `string \| null` | Posting date formatted as `YYYY-MM-DD` in local time. |
| `results[].time` | `string \| null` | Posting time formatted as `HH:MM:SS` in local time. |
| `results[].error` | `string \| null` | Diagnostic error explanation if failed; `null` if successful. |

---

### 2.4 Error Responses

#### Response: `422 Unprocessable Entity` (Validation Failure)
Returned when input constraints are violated (e.g. message $>200$ chars, missing CTA link, multiple links).

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

#### Response: `500 Internal Server Error` (Unexpected System Exception)
Returned only in the event of an unrecoverable system exception in the orchestration engine.

```json
{
  "detail": "An internal system error occurred while orchestrating platform broadcasts."
}
```

---

## 3. Auxiliary SRE Probes

### 3.1 `GET /health` (Liveness Probe)
- **Response:** `200 OK`
- **Body:** `{"status": "ok"}`
- **Purpose:** Used by container orchestrators and keepalive cron pingers to verify the server process is alive.

### 3.2 `GET /ready` (Readiness Probe)
- **Response:** `200 OK`
- **Body:** `{"status": "ready", "platforms_configured": 5}`
- **Purpose:** Verifies environment variable bindings and service readiness before routing traffic.
