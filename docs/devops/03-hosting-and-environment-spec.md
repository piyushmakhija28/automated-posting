# Level 7: DevOps & Container Architecture — Production Hosting & Environment Configuration

**Document ID:** `DOC-OPS-03-HOSTING`  
**Project:** `automated-posting`  
**Author:** Principal Software Architect
**Reviewer:** Staff Backend Engineering Lead
**Status:** APPROVED  
**Standard:** 12-Factor App Principles, Render.com Web Services Blueprint

---

## 1. Hosting Architecture on Render.com

The production service is hosted on **Render.com** as a containerized Web Service:
- **Build Type:** Docker
- **Region:** Oregon (US West) / Frankfurt (EU Central)
- **Instance Type:** Free Tier / Starter
- **Auto-Deploy:** Enabled on push to `main` branch of `https://github.com/piyushmakhija28/automated-posting`
- **HTTPS Termination:** Automatic zero-configuration SSL/TLS managed by Render via Let's Encrypt.
- **Assigned Domain:** `https://automated-posting-dxora.onrender.com`

---

## 2. Environment Variables Specification (`.env`)

```ini
# ==============================================================================
# APPLICATION SETTINGS
# ==============================================================================
APP_NAME="Automated Multi-Platform Posting Engine"
APP_ENV=production
APP_PORT=4000
DEBUG=false
LOG_LEVEL=INFO

# ==============================================================================
# PLATFORM CREDENTIALS (SENSITIVE - NEVER COMMIT TO GIT)
# ==============================================================================
# 1. LinkedIn API (OAuth 2.0 UGC Posts)
LINKEDIN_ACCESS_TOKEN=""
LINKEDIN_PERSON_URN=""

# 2. Dev.to API (Forem REST API)
DEVTO_API_KEY=""

# 3. Hashnode GraphQL API
HASHNODE_API_KEY=""
HASHNODE_PUBLICATION_ID=""

# 4. Mastodon REST API
MASTODON_ACCESS_TOKEN=""
MASTODON_BASE_URL="https://mastodon.social"

# 5. Telegram Bot API
TELEGRAM_BOT_TOKEN=""
TELEGRAM_CHANNEL_ID=""
```

---

## 3. Deployment Verification Commands

Once deployed to Render.com, verify the live deployment using these cURL commands:

```bash
# 1. Verify Liveness Probe
curl -i https://automated-posting-dxora.onrender.com/health

# 2. Verify Readiness Probe
curl -i https://automated-posting-dxora.onrender.com/ready

# 3. Test Live Broadcast Endpoint
curl -X POST https://automated-posting-dxora.onrender.com/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "Deploying resilient publishing pipelines on modern cloud infrastructure! https://dxora.com"}'
```
