"""Inbound request Form models with 7-Stage sequential validation pipeline."""

import ipaddress
import re
import unicodedata
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator

from app.core.constants import ErrorCodeConstants, ValidationMessageConstants
from app.core.exceptions import MessageValidationError, SecurityThreatError, UrlExtractionError


class PostingForm(BaseModel):
    """Inbound request form for the POST /posting endpoint.

    Implements strict DTO/Form separation and ordered 7-stage validation sequence.
    """

    model_config = ConfigDict(
        extra="ignore",
        frozen=False,
        str_strip_whitespace=False,
    )

    message: str = Field(
        ...,
        description="The content to broadcast across all configured platforms (<= 200 chars, exactly 1 URL).",
        examples=[
            "Excited to announce our new product update! Read more here: https://example.com/update"
        ],
    )

    _cleaned_message: str = PrivateAttr(default="")
    _extracted_url: str = PrivateAttr(default="")

    @property
    def cleaned_message(self) -> str:
        """Returns the canonicalized and sanitized message text."""
        return self._cleaned_message or self.message

    @property
    def extracted_url(self) -> str:
        """Returns the verified single CTA URL extracted from the message."""
        return self._extracted_url

    def model_post_init(self, __context: object) -> None:
        """Extracts and binds canonicalized message and extracted CTA URL after validation."""
        super().model_post_init(__context)
        self._cleaned_message = self.message

        url_regex = re.compile(
            r"https?://(?:[a-zA-Z0-9\-._~%!$&'()*+,;=]+@)?(?:[a-zA-Z0-9\-._~%]+|\[[a-fA-F0-9:.]+\])(?::\d+)?(?:/[^\s]*)?",
            re.IGNORECASE,
        )
        matches = url_regex.findall(self.message)
        if matches:
            self._extracted_url = matches[0].rstrip(".,;!?:)'\"")

    @field_validator("message", mode="before")
    @classmethod
    def validate_and_sanitize_message(cls, raw_value: object) -> str:
        """Executes the ordered 7-stage validation and sanitization sequence.

        Sequence:
        Stage 1: Null & Type Screening
        Stage 2: Unicode Normalization (NFKC), Zero-Width Stripping & Trojan Source Detection
        Stage 3: Character Length Enforcement (<= 200 unicode characters)
        Stage 4: URL Extraction & Single-URL Invariant Check
        Stage 5: URL Protocol & SSRF Network Screening
        Stage 6: Threat & Prompt Injection Detection
        Stage 7: Canonicalization & Payload Construction
        """
        # Stage 1: Null & Type Screening
        if raw_value is None:
            raise MessageValidationError(
                ValidationMessageConstants.MSG_NOT_NULL,
                error_code=ErrorCodeConstants.ERR_MISSING_FIELD,
            )
        if not isinstance(raw_value, str):
            raise MessageValidationError(
                ValidationMessageConstants.MSG_NOT_BLANK,
                error_code=ErrorCodeConstants.ERR_EMPTY_MESSAGE,
            )

        # Stage 2: Trojan Source Detection, Control Chars & Invisible Character Stripping
        if "\x00" in raw_value:
            raise SecurityThreatError(
                "Null byte control characters are strictly prohibited.",
                threat_type="NULL_BYTE_INJECTION",
                error_code=ErrorCodeConstants.ERR_MALICIOUS_CONTROL_CHARS,
            )

        bidi_pattern = re.compile(r"[\u202A-\u202E\u2066-\u2069]")
        if bidi_pattern.search(raw_value):
            raise SecurityThreatError(
                ValidationMessageConstants.MSG_SUSPICIOUS_PAYLOAD,
                threat_type="BIDI_OVERRIDE_INJECTION",
                error_code=ErrorCodeConstants.ERR_MALICIOUS_CONTROL_CHARS,
            )

        normalized = unicodedata.normalize("NFKC", raw_value)
        cleaned = re.sub(r"[\u200B-\u200D\uFEFF\u00AD]", "", normalized)
        stripped = cleaned.strip()

        if not stripped:
            raise MessageValidationError(
                ValidationMessageConstants.MSG_NOT_BLANK,
                error_code=ErrorCodeConstants.ERR_EMPTY_MESSAGE,
            )

        # Collapse consecutive internal whitespace to prevent layout breakage
        collapsed = re.sub(r"[ \t]+", " ", stripped)

        # Stage 3: Character Length Enforcement (<= 200 unicode characters)
        if len(collapsed) > 200:
            raise MessageValidationError(
                ValidationMessageConstants.MSG_TOO_LONG,
                error_code=ErrorCodeConstants.ERR_CHAR_LIMIT_EXCEEDED,
            )

        # Stage 4: URL Extraction & Count Invariant (Exactly 1 CTA URL)
        url_regex = re.compile(
            r"[a-zA-Z][a-zA-Z0-9+.-]*://(?:[a-zA-Z0-9\-._~%!$&'()*+,;=]+@)?(?:[a-zA-Z0-9\-._~%]+|\[[a-fA-F0-9:.]+\])(?::\d+)?(?:/[^\s]*)?",
            re.IGNORECASE,
        )
        raw_matches = url_regex.findall(collapsed)
        cleaned_matches = [m.rstrip(".,;!?:)'\"") for m in raw_matches]

        if len(cleaned_matches) == 0:
            raise UrlExtractionError(
                ValidationMessageConstants.MSG_URL_REQUIRED,
                count=0,
                error_code=ErrorCodeConstants.ERR_MISSING_CTA_URL,
            )
        if len(cleaned_matches) > 1:
            raise UrlExtractionError(
                ValidationMessageConstants.MSG_URL_MULTIPLE.format(count=len(cleaned_matches)),
                count=len(cleaned_matches),
                error_code=ErrorCodeConstants.ERR_MULTIPLE_CTA_URLS,
            )

        target_url = cleaned_matches[0]

        # Stage 5: URL Scheme & SSRF Protection
        parsed = urlparse(target_url)
        if parsed.scheme.lower() not in ("http", "https"):
            raise MessageValidationError(
                ValidationMessageConstants.MSG_URL_INVALID_SCHEME,
                error_code=ErrorCodeConstants.ERR_INVALID_URL_SCHEME,
            )
        if not parsed.hostname:
            raise MessageValidationError(
                ValidationMessageConstants.MSG_URL_INVALID_SCHEME,
                error_code=ErrorCodeConstants.ERR_INVALID_URL_SCHEME,
            )

        hostname = parsed.hostname.lower()
        blocked_hostnames = {
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "::1",
            "169.254.169.254",
            "metadata.google.internal",
            "instance-data",
        }
        if hostname in blocked_hostnames:
            raise SecurityThreatError(
                ValidationMessageConstants.MSG_URL_SSRF_BLOCKED,
                threat_type="SSRF_PROHIBITED_HOST",
                error_code=ErrorCodeConstants.ERR_SSRF_PROHIBITED,
            )

        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise SecurityThreatError(
                    ValidationMessageConstants.MSG_URL_SSRF_BLOCKED,
                    threat_type="SSRF_PRIVATE_IP",
                    error_code=ErrorCodeConstants.ERR_SSRF_PROHIBITED,
                )
        except ValueError:
            pass

        # Stage 6: Threat & Prompt Injection Screening
        injection_pattern = re.compile(
            r"(ignore\s+all\s+previous\s+instructions|system\s+prompt|drop\s+database|drop\s+table)",
            re.IGNORECASE,
        )
        if injection_pattern.search(collapsed):
            raise SecurityThreatError(
                ValidationMessageConstants.MSG_PROMPT_INJECTION_DETECTED,
                threat_type="PROMPT_INJECTION",
                error_code=ErrorCodeConstants.ERR_PROMPT_INJECTION,
            )

        # Stage 7: Canonicalization Complete
        return collapsed
