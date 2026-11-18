# Level 1.6: Platform API Research & Integration Specifications

**Document ID:** `DOC-04-PLATFORM-RESEARCH`  
**Project:** `automated-posting`  
**Author:** Principal Software Architect
**Reviewer:** Staff Backend Engineering Lead
**Status:** APPROVED  
**Standard:** Level 2.3 Documentation Governance (`rules/11-documentation-files.md`)

---

## 1. Research Overview & Scope
To satisfy the requirements of Section 3.A of the Practical Test, we conducted exhaustive research into the official developer documentation of 5 selected third-party platforms. This document details the exact authentication mechanisms, endpoints, payload structures, character limits, rate limits, edge-case gotchas, and sample HTTP calls for each platform.

---

## 2. Platform 1: LinkedIn (UGC Posts API)

### 2.1 API Metadata
- **Official Documentation:** [LinkedIn Community Management API - UGC Posts](https://learn.microsoft.com/en-us/linkedin/marketing/integrations/community-management/shares/ugc-post-api)
- **Protocol:** REST over HTTPS
- **Target Endpoint:** `POST https://api.linkedin.com/v2/ugcPosts`
- **Authentication Method:** OAuth 2.0 (3-Legged User Token)
- **Required Scopes:** `w_member_social`, `openid`, `profile`

### 2.2 Request Headers & Payload
```http
POST /v2/ugcPosts HTTP/1.1
Host: api.linkedin.com
Authorization: Bearer <LINKEDIN_ACCESS_TOKEN>
X-Restli-Protocol-Version: 2.0.0
Content-Type: application/json

{
  "author": "urn:li:person:<PERSON_URN>",
  "lifecycleState": "PUBLISHED",
  "specificContent": {
    "com.linkedin.ugc.ShareContent": {
      "shareCommentary": {
        "text": "Check out our latest platform release and scale your online visibility! https://example.com"
      },
      "shareMediaCategory": "ARTICLE",
      "media": [
        {
          "status": "READY",
          "originalUrl": "https://example.com"
        }
      ]
    }
  },
  "visibility": {
    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
  }
}
```

### 2.3 Response Structure
- **Success Code:** `HTTP 201 Created`
- **Identifier Extraction:** The response contains an `id` field formatted as `urn:li:share:7123456789`.
- **Public URL Construction:** `https://www.linkedin.com/feed/update/{id}`

### 2.4 Gotchas & Mitigations (ISSUE-001)
- **Token Expiry:** LinkedIn User tokens expire every 60 days. The adapter catches HTTP 401 and classifies the error explicitly: `"LinkedIn OAuth token expired or invalid — refresh token required"`.
- **Author URN:** Must match the authenticated user URN (`urn:li:person:...`). Managed via `LINKEDIN_PERSON_URN` in `.env`.

---

## 3. Platform 2: Dev.to (Forem Articles API)

### 3.1 API Metadata
- **Official Documentation:** [Forem API Documentation (Dev.to)](https://developers.forem.com/api/v1#tag/articles/operation/createArticle)
- **Protocol:** REST over HTTPS
- **Target Endpoint:** `POST https://dev.to/api/articles`
- **Authentication Method:** Static API Key passed in request header (`api-key`)
- **Key Generation:** Obtained instantly under Dev.to Account Settings $\to$ Extensions $\to$ Dev.to Community API Keys.

### 3.2 Request Headers & Payload
```http
POST /api/articles HTTP/1.1
Host: dev.to
api-key: <DEVTO_API_KEY>
Content-Type: application/json

{
  "article": {
    "title": "Exciting Announcement: Scale Your Online Visibility",
    "body_markdown": "Check out our latest business platform and grow your online visibility. https://example.com",
    "published": true,
    "tags": ["tech", "updates", "announcement"]
  }
}
```

### 3.3 Response Structure
- **Success Code:** `HTTP 201 Created`
- **Public URL Extraction:** The JSON response directly provides the canonical public URL in the `url` attribute (e.g. `https://dev.to/piyush/exciting-announcement-abc123`).

### 3.4 Gotchas & Mitigations (ISSUE-002)
- **Article vs Status Mismatch:** Dev.to requires a `title` and markdown `body`. The adapter synthesizes a clean title from the first 60 characters of the message, strips URL artifacts from the title, and wraps the full message with the CTA URL as the body markdown.

---

## 4. Platform 3: Hashnode (GraphQL API)

### 4.1 API Metadata
- **Official Documentation:** [Hashnode Public GraphQL API](https://apidocs.hashnode.com/)
- **Protocol:** GraphQL over HTTPS
- **Target Endpoint:** `POST https://gql.hashnode.com`
- **Authentication Method:** Personal Access Token passed in `Authorization` header
- **Key Generation:** Hashnode Account Settings $\to$ Developer $\to$ Personal Access Token.

### 4.2 Request Headers & Mutation Payload
```http
POST / HTTP/1.1
Host: gql.hashnode.com
Authorization: <HASHNODE_API_KEY>
Content-Type: application/json

{
  "query": "mutation PublishPost($input: PublishPostInput!) { publishPost(input: $input) { post { id title url } } }",
  "variables": {
    "input": {
      "title": "Platform Release Announcement",
      "contentMarkdown": "Check out our latest business platform and grow your online visibility. https://example.com",
      "publicationId": "<HASHNODE_PUBLICATION_ID>",
      "tags": []
    }
  }
}
```

### 4.3 Response Structure
- **Success Code:** `HTTP 200 OK`
- **Public URL Extraction:** `data.publishPost.post.url`
- **Error Extraction:** GraphQL returns HTTP 200 even on mutation errors; the adapter checks for the presence of `errors` in the response body.

### 4.4 Gotchas & Mitigations (ISSUE-003)
- **Publication ID Requirement:** The mutation requires a valid `publicationId`. If omitted, the mutation rejects the call. Parameterized via `HASHNODE_PUBLICATION_ID` in `.env`.

---

## 5. Platform 4: Mastodon (Statuses REST API)

### 5.1 API Metadata
- **Official Documentation:** [Mastodon API Documentation - Post a Status](https://docs.joinmastodon.org/methods/statuses/#create)
- **Protocol:** REST over HTTPS
- **Target Endpoint:** `POST {MASTODON_BASE_URL}/api/v1/statuses` (default: `https://mastodon.social/api/v1/statuses`)
- **Authentication Method:** OAuth Bearer Token (`Authorization: Bearer <TOKEN>`)
- **Key Generation:** Mastodon Preferences $\to$ Development $\to$ New Application (select `write:statuses` scope).

### 5.2 Request Headers & Payload
```http
POST /api/v1/statuses HTTP/1.1
Host: mastodon.social
Authorization: Bearer <MASTODON_ACCESS_TOKEN>
Content-Type: application/json

{
  "status": "Check out our latest business platform and grow your online visibility. https://example.com",
  "visibility": "public"
}
```

### 5.3 Response Structure
- **Success Code:** `HTTP 200 OK`
- **Public URL Extraction:** The response contains an attribute `url` pointing to the public toot (e.g. `https://mastodon.social/@piyush/112345678901234567`).

### 5.4 Gotchas & Mitigations (ISSUE-011)
- **Federated Base URL:** Because Mastodon is federated across hundreds of independent server instances, the base URL must be configurable. The adapter reads `MASTODON_BASE_URL` from settings, defaulting to `https://mastodon.social`.

---

## 6. Platform 5: Telegram (Bot API)

### 6.1 API Metadata
- **Official Documentation:** [Telegram Bot API - sendMessage](https://core.telegram.org/bots/api#sendmessage)
- **Protocol:** REST over HTTPS
- **Target Endpoint:** `POST https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/sendMessage`
- **Authentication Method:** Bot Secret Token embedded in the URL path
- **Key Generation:** Instantly created via Telegram's `@BotFather` bot.

### 6.2 Request Headers & Payload
```http
POST /bot<TELEGRAM_BOT_TOKEN>/sendMessage HTTP/1.1
Host: api.telegram.org
Content-Type: application/json

{
  "chat_id": "@my_public_announcements",
  "text": "Check out our latest business platform and grow your online visibility. https://example.com",
  "parse_mode": "HTML"
}
```

### 6.3 Response Structure
- **Success Code:** `HTTP 200 OK`
- **Response Format:**
```json
{
  "ok": true,
  "result": {
    "message_id": 142,
    "chat": {
      "id": -1001234567890,
      "title": "Announcements",
      "username": "my_public_announcements",
      "type": "channel"
    },
    "date": 1700300000,
    "text": "..."
  }
}
```
- **Public URL Construction:** For public channels, the URL is deterministically synthesized as: `https://t.me/{username}/{message_id}` (e.g. `https://t.me/my_public_announcements/142`).

### 6.4 Gotchas & Mitigations (ISSUE-006)
- **Channel Administrator Privileges:** The Telegram Bot **must** be added as an Administrator to the target public channel with "Post Messages" permission. If not, the API returns `400 Bad Request: chat not found` or `403 Forbidden: bot is not a member of the channel`. The adapter traps these specific codes and returns clear diagnostic advice.

---

## 7. Comparative Platform Matrix

| Platform | Protocol | Payload Limit | Rate Limit | Auth Type | Free Access? |
|---|---|---|---|---|---|
| **LinkedIn** | REST | 3,000 chars | ~100 posts/day | OAuth 2.0 User Token | ✅ Yes |
| **Dev.to** | REST | Unlimited | 30 req/30 sec | Static API Key | ✅ Yes |
| **Hashnode** | GraphQL | Unlimited | 100 req/min | Personal Access Token | ✅ Yes |
| **Mastodon** | REST | 500 chars | 300 req/5 min | OAuth Bearer Token | ✅ Yes |
| **Telegram** | REST | 4,096 chars | 20 msgs/min | Bot Secret Token | ✅ Yes |
