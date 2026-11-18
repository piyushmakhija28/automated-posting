# 📢 Automated Multi-Platform Posting System

> **Dxora Technologies – Python Practical Test Submission**
> **Candidate:** Piyush Makhija
> **Deadline:** 22nd November 2026

---

## 📌 Project Overview

This project is an **Automated Multi-Platform Posting API** built with **FastAPI** that accepts a short message (max 200 characters with a CTA link) and **automatically publishes it across 5+ third-party platforms** via their official APIs — simultaneously, with graceful error handling per platform.

---

## 🧠 My Understanding of the Problem

### What is the core problem?
Businesses and marketers need to publish the same message across multiple platforms (social media, blogging sites, dev communities) manually — which is time-consuming and error-prone. This API automates that entire flow in a single POST request.

### What does this API solve?
Given a message like:
```
"Check out our latest business platform and grow your online visibility. https://example.com"
```
The API:
1. **Validates** the message (length ≤ 200 chars, exactly 1 valid URL)
2. **Posts in parallel** to all 5+ integrated platforms
3. **Returns structured results** — success/failure per platform, with posted URL and timestamp
4. **Never blocks** — if one platform fails, others continue posting

### Why is this challenging?
- Each platform has a **completely different API** (OAuth, API keys, different auth flows)
- Some platforms have **character limits** that differ from our 200 char input limit
- **Rate limits** and **API availability** vary per platform
- Need **parallel execution** (not sequential) for fast response
- Must handle **partial failures gracefully** — 1 platform down ≠ full API failure

---

## 🏗️ Architecture & Design Decisions

### High-Level Flow

```
Client → POST /posting { "message": "..." }
              ↓
        Input Validation
        (length, URL presence, URL validity)
              ↓
        Platform Adapter Layer
        ┌─────────────────────────────────────┐
        │  LinkedIn  │  Dev.to  │  Blogger    │
        │  Hashnode  │  Mastodon│  Telegram   │
        └─────────────────────────────────────┘
              ↓ (asyncio.gather — all in parallel)
        Collect Results (success + failed)
              ↓
        Structured JSON Response
```

### Technology Stack

| Component | Technology | Reason |
|---|---|---|
| **Framework** | FastAPI | Async-native, perfect for parallel API calls |
| **Server** | Uvicorn | ASGI server for async FastAPI |
| **HTTP Client** | HTTPX (async) | Async HTTP calls to multiple platforms simultaneously |
| **Validation** | Pydantic v2 | Strict message + URL validation |
| **Concurrency** | `asyncio.gather()` | Parallel posting — no waiting for one platform |
| **Config** | python-dotenv | Secure credential management |

---

## 🌐 Integrated Platforms

### Why These 5 Platforms?

| Platform | Why Chosen | API Type | Auth Method |
|---|---|---|---|
| **LinkedIn** | #1 professional network, strong business reach | REST API | OAuth 2.0 |
| **Dev.to** | Popular developer community, free public API | REST API | API Key |
| **Hashnode** | Developer blogging platform, GraphQL API | GraphQL | API Key |
| **Mastodon** | Open-source, decentralized, easy API | REST API | OAuth Token |
| **Telegram Channel** | Instant delivery to subscribers, bot API | Bot API | Bot Token |

**Research rationale:** I chose platforms with:
1. ✅ Free API access (no enterprise plan required)
2. ✅ Clear official documentation
3. ✅ Programmatic posting support
4. ✅ Public content visibility
5. ✅ Different audience types (professional, developer, general)

> **Note on Twitter/X:** X API now requires paid access ($100+/month for Basic write access). Not included as free-tier posting is no longer available.
> **Note on Facebook:** Facebook Pages API requires app review for `pages_manage_posts` permission — takes weeks. Not feasible for a time-limited test.

---

## 📁 Project Structure

```
automated-posting/
│
├── app/
│   ├── main.py                  # FastAPI app, POST /posting endpoint
│   ├── schemas.py               # Pydantic models: request + response
│   ├── config.py                # Settings, env vars
│   │
│   ├── platforms/
│   │   ├── base.py              # Abstract BasePlatform class
│   │   ├── linkedin.py          # LinkedIn API integration
│   │   ├── devto.py             # Dev.to API integration
│   │   ├── hashnode.py          # Hashnode GraphQL integration
│   │   ├── mastodon.py          # Mastodon API integration
│   │   └── telegram.py         # Telegram Bot API integration
│   │
│   └── services/
│       └── posting_service.py   # Orchestrates parallel posting
│
├── tests/
│   └── test_posting.py          # Unit + integration tests
│
├── .env.example                 # Template (no real secrets)
├── requirements.txt
└── README.md
```

---

## 🔌 API Specification

### Endpoint

```http
POST http://localhost:4000/posting
```

### Request Body

```json
{
  "message": "Check out our latest business platform and grow your online visibility. https://example.com"
}
```

### Input Validation Rules

| Rule | Requirement |
|---|---|
| Max length | 200 characters |
| CTA link | Exactly 1 valid URL must be present |
| URL format | Must be a valid, reachable HTTP/HTTPS URL |
| Empty message | Not allowed |

### Response Structure

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
      "posted_url": "https://www.linkedin.com/feed/update/urn:li:share:123456",
      "public_access": true,
      "date": "2026-11-18",
      "time": "12:30:00",
      "error": null
    },
    {
      "platform": "Dev.to",
      "status": "success",
      "posted_url": "https://dev.to/piyush/my-post-title-abc123",
      "public_access": true,
      "date": "2026-11-18",
      "time": "12:30:01",
      "error": null
    },
    {
      "platform": "Hashnode",
      "status": "success",
      "posted_url": "https://hashnode.com/post/abc123",
      "public_access": true,
      "date": "2026-11-18",
      "time": "12:30:01",
      "error": null
    },
    {
      "platform": "Mastodon",
      "status": "success",
      "posted_url": "https://mastodon.social/@piyush/123456",
      "public_access": true,
      "date": "2026-11-18",
      "time": "12:30:02",
      "error": null
    },
    {
      "platform": "Telegram",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Channel not found or bot not admin"
    }
  ]
}
```

---

## 🔑 Platform API Research

### LinkedIn API
- **Docs:** https://learn.microsoft.com/en-us/linkedin/marketing/integrations/community-management/shares/ugc-post-api
- **Auth:** OAuth 2.0 (3-legged)
- **Endpoint:** `POST https://api.linkedin.com/v2/ugcPosts`
- **Post Type:** `com.linkedin.ugc.ShareContent`
- **Visibility:** `PUBLIC`

### Dev.to API
- **Docs:** https://developers.forem.com/api
- **Auth:** API Key in header (`api-key`)
- **Endpoint:** `POST https://dev.to/api/articles`
- **Free:** ✅ Yes, free API key on signup

### Hashnode API
- **Docs:** https://apidocs.hashnode.com
- **Auth:** API Key in header (`Authorization`)
- **Type:** GraphQL (`POST https://gql.hashnode.com`)
- **Free:** ✅ Yes

### Mastodon API
- **Docs:** https://docs.joinmastodon.org/api/
- **Auth:** OAuth Bearer Token
- **Endpoint:** `POST https://mastodon.social/api/v1/statuses`
- **Free:** ✅ Yes, open source

### Telegram Bot API
- **Docs:** https://core.telegram.org/bots/api
- **Auth:** Bot Token (from @BotFather)
- **Endpoint:** `POST https://api.telegram.org/bot{TOKEN}/sendMessage`
- **Free:** ✅ Yes

---

## ⚡ Key Technical Decisions

### 1. Parallel Posting with `asyncio.gather()`
All platforms are posted **simultaneously**, not sequentially. Response time ≈ slowest single platform (not sum of all).

### 2. Abstract Base Platform Class
Each platform extends `BasePlatform` with a standard `post(message: str) → PlatformResult` interface. Adding a new platform = just add one file.

### 3. Validation Approach
- Pydantic validator checks message length ≤ 200
- Regex extracts URLs from message
- Exactly 1 URL required (not 0, not 2+)
- URL validated with `httpx.head()` check

### 4. Per-Platform Error Isolation
Each platform runs in its own `try/except`. One failure never kills others. All results collected regardless.

---

## 🛡️ Security

- All API keys/tokens stored in `.env` (never committed)
- `.env.example` provided with placeholder values
- Input sanitized before sending to any API
- No internal network URLs accepted in message CTA

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.10+
- API keys/tokens for each platform (see `.env.example`)

### Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/piyushmakhija28/automated-posting.git
cd automated-posting

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Add your API keys to .env

# 5. Run the server
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
```

### Environment Variables

```env
# LinkedIn
LINKEDIN_ACCESS_TOKEN=your_linkedin_oauth_token
LINKEDIN_PERSON_URN=urn:li:person:your_id

# Dev.to
DEVTO_API_KEY=your_devto_api_key

# Hashnode
HASHNODE_API_KEY=your_hashnode_api_key
HASHNODE_PUBLICATION_ID=your_publication_id

# Mastodon
MASTODON_ACCESS_TOKEN=your_mastodon_token
MASTODON_BASE_URL=https://mastodon.social

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHANNEL_ID=@your_channel
```

### Test the API

```bash
# Using curl
curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "Check out our latest platform! https://example.com"}'

# API Documentation (Swagger UI)
open http://localhost:4000/docs
```

---

## 📊 Evaluation Criteria Coverage

| Criteria | Marks | Status |
|---|---:|---|
| FastAPI implementation & API structure | 15 | 🔄 In Progress |
| Input validation | 15 | 🔄 In Progress |
| Platform research & API integration | 25 | 🔄 In Progress |
| Automatic multi-platform posting | 20 | 🔄 In Progress |
| Error handling & response management | 10 | 🔄 In Progress |
| Code quality & GitHub documentation | 15 | ✅ Done |
| **Total** | **100** | |

---

## 👨‍💻 About the Developer

**Piyush Makhija**
- Full Stack Developer | Python & API Integration Enthusiast
- GitHub: [@piyushmakhija28](https://github.com/piyushmakhija28)

---

*Submission for Dxora Technologies Python Practical Test*
*Deadline: 22nd November 2026*
