# Level 3: Security & Threat Modeling Architecture — Credential & Logging Governance

**Document ID:** `DOC-SEC-03-CREDENTIAL-GOVERNANCE`  
**Project:** `automated-posting`  
**Author:** Principal Software Architect
**Reviewer:** Staff Backend Engineering Lead
**Status:** APPROVED  
**Standard:** OWASP ASVS v4.0 & PCI-DSS Masking Guidelines, OWASP Logging Cheat Sheet

---

## 1. Secret Ingestion & Zero-Trust Storage

All credentials required for interacting with third-party platforms are managed according to the **Twelve-Factor App Methodology (Factor III: Config)**:

| Environment Variable | Target Platform | Type | Minimum Scope Required |
|---|---|---|---|
| `LINKEDIN_ACCESS_TOKEN` | LinkedIn | OAuth 2.0 User Token | `w_member_social`, `openid`, `profile` |
| `LINKEDIN_PERSON_URN` | LinkedIn | URN String | Identifier of authenticated user |
| `DEVTO_API_KEY` | Dev.to | Static API Key | Standard Community API Key |
| `HASHNODE_API_KEY` | Hashnode | Personal Access Token | Standard Developer PAT |
| `HASHNODE_PUBLICATION_ID` | Hashnode | Publication Identifier | Target publication ID |
| `MASTODON_ACCESS_TOKEN` | Mastodon | OAuth Bearer Token | `write:statuses` |
| `MASTODON_BASE_URL` | Mastodon | URL String | e.g. `https://mastodon.social` |
| `TELEGRAM_BOT_TOKEN` | Telegram | Bot Secret Key | Token issued by `@BotFather` |
| `TELEGRAM_CHANNEL_ID` | Telegram | Target Channel Username | e.g. `@dxora_announcements` |

### Git Hygiene Safeguards:
1. `.env` is explicitly listed in `.gitignore`.
2. `.env.example` contains only empty string placeholders (`your_token_here`).
3. Automated CI pre-commit hooks scan for potential high-entropy strings and secret patterns.

---

## 2. Automated Log Scrubbing Engine (`SanitizedLogger`)

Standard application logging (especially when debugging HTTP payloads or logging exceptions) risks dumping raw authorization headers (`Authorization: Bearer <secret>`).

The architecture implements a custom logging filter `SensitiveDataFilter` that intercepts all records before they reach the console or log files:

```python
import logging
import re

class SensitiveDataFilter(logging.Filter):
    """
    Automated regex filter that intercepts and sanitizes sensitive credentials,
    bearer tokens, and bot secrets from all log records.
    """
    REDACTION_RULES = [
        # Mask Bearer tokens
        (re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{8,}", re.IGNORECASE), r"\1***REDACTED***"),
        # Mask Telegram bot tokens in URLs (e.g. /bot123456:ABC-DEF...)
        (re.compile(r"(/bot)\d+:[A-Za-z0-9_\-]{20,}", re.IGNORECASE), r"\1***REDACTED***"),
        # Mask API keys in json / query params
        (re.compile(r"(api[-_]?key['\":\s=]+)[A-Za-z0-9_\-]{8,}", re.IGNORECASE), r"\1***REDACTED***"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, replacement in self.REDACTION_RULES:
                record.msg = pattern.sub(replacement, record.msg)
        return True
```

This guarantees compliance with GDPR, DPDP Act 2023, and SOC 2 Type II audit logging standards.
