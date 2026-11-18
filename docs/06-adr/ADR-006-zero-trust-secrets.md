# ADR-006: Zero-Trust Secret Management & Sanitized Logging

**Status:** ACCEPTED  
**Date:** 2026-11-18  
**Author:** Lead Application Security Architect
**Reviewer:** Technical Architecture Review Board
**Governed Issue:** ISSUE-009 (Secret Leakage in Logs)  

---

## 1. Context & Problem Statement
The application requires API keys, bot tokens, and OAuth Bearer tokens for 5 third-party platforms. If these credentials are committed to git repositories, embedded in source code, or emitted in stdout/stderr log streams, severe security breaches occur (credential theft, unauthorized impersonation, bot hijacking).

## 2. Decision Drivers
- OWASP API Security Top 10 API2:2023 (Broken Authentication) and API9:2023 (Improper Inventory).
- The Twelve-Factor App Principle III (Config in environment).
- Zero-exposure in public GitHub repository (`piyushmakhija28/automated-posting`).
- Automatic prevention of accidental logging of HTTP authorization headers.

## 3. Decision Outcome
**Chosen Architecture:** **Pydantic-Settings Injection + Log Stream Token Redaction**

### 3.1 Environment Variable Isolation
All secrets are externalized to environment variables and loaded via `pydantic-settings`:
- `LINKEDIN_ACCESS_TOKEN`
- `DEVTO_API_KEY`
- `HASHNODE_API_KEY`, `HASHNODE_PUBLICATION_ID`
- `MASTODON_ACCESS_TOKEN`, `MASTODON_BASE_URL`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID`

`.env` is strictly added to `.gitignore`. A sanitized template `.env.example` is committed to guide developers without revealing real secrets.

### 3.2 Automated Log Sanitization (`SanitizedLogger`)
A custom Python logging `Filter` and `Formatter` intercepts all log records before output:
```python
class SensitiveDataFilter(logging.Filter):
    PATTERNS = [
        (re.compile(r"Bearer\s+([A-Za-z0-9_\-\.]+)", re.IGNORECASE), "Bearer ***REDACTED***"),
        (re.compile(r"bot(\d+:[A-Za-z0-9_\-]+)", re.IGNORECASE), "bot***REDACTED***"),
        (re.compile(r"api[-_]?key['\":\s]+([A-Za-z0-9_\-]+)", re.IGNORECASE), "api_key=***REDACTED***"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, repl in self.PATTERNS:
                record.msg = pattern.sub(repl, record.msg)
        return True
```

### Positive Consequences:
- Even if an unhandled exception or debug dump prints full HTTP headers, authentication tokens are reliably scrubbed before leaving the process boundary.
- Zero risk of git credential leakage.
