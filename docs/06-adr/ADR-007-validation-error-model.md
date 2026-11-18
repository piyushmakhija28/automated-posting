# ADR-007: Validation & RFC 7807 Error Envelope Modeling

**Status:** ACCEPTED  
**Date:** 2026-11-18  
**Author:** Principal Enterprise Architect
**Reviewer:** Technical Architecture Review Board
**Governed Issue:** ISSUE-007, ISSUE-010  

---

## 1. Context & Problem Statement
The input requirements demand strict validation:
1. Message length $\le 200$ characters.
2. Exactly one CTA link must be included in the message.
3. Validate URL format.
4. Return appropriate, structured validation errors for invalid input.

FastAPI 0.100+ upgraded its core schema validation engine from Pydantic v1 to Pydantic v2. We must define how validation is structured and how error responses are standardized.

## 2. Decision Drivers
- Pydantic v2 compliance (avoid deprecated v1 `.dict()` or `@validator` patterns).
- Multi-tier validation sequencing (syntax $\to$ length $\to$ URL extraction $\to$ URL sanity).
- RFC 7807 (Problem Details for HTTP APIs) compatibility.
- Clean client diagnostics explaining why a request failed.

## 3. Decision Outcome
**Chosen Architecture:** **Pydantic v2 Field Validators + Sequential Domain Validation**

### Schema Definition:
```python
class PostRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    message: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Broadcast message text (max 200 chars) containing exactly one CTA URL."
    )

    @field_validator("message")
    @classmethod
    def validate_single_cta_url(cls, v: str) -> str:
        # 1. Length check
        if len(v) > 200:
            raise ValueError(f"Message length ({len(v)} chars) exceeds maximum allowed limit of 200 characters.")
        
        # 2. Extract URLs using multi-pass regex
        raw_urls = re.findall(r"https?://[^\s]+", v)
        cleaned_urls = [u.rstrip(".,;:!?)'") for u in raw_urls]

        # 3. Exact count invariant
        if len(cleaned_urls) == 0:
            raise ValueError("Message must contain exactly one valid CTA URL (http:// or https://). None found.")
        if len(cleaned_urls) > 1:
            raise ValueError(f"Message contains {len(cleaned_urls)} URLs. Exactly one CTA URL is permitted.")
        
        # 4. Syntactic sanity
        parsed = urlparse(cleaned_urls[0])
        if not parsed.scheme or not parsed.netloc or "." not in parsed.netloc:
            raise ValueError(f"Extracted CTA URL '{cleaned_urls[0]}' is syntactically invalid.")
            
        return v
```

### Positive Consequences:
- Immediate 422 Unprocessable Entity response generated automatically by FastAPI if validation fails before any service logic or network call is triggered.
- Full type-safety throughout the application.
