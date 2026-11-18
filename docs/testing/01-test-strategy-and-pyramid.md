# Level 6: Testing Strategy & Test Suites — Test Pyramid & Strategy

**Document ID:** `DOC-TST-01-STRATEGY`  
**Project:** `automated-posting`  
**Author:** Principal Software Architect
**Reviewer:** Staff Backend Engineering Lead
**Status:** APPROVED  
**Standard:** Mike Cohn Test Pyramid, ISO/IEC/IEEE 29119 Test Patterns & Pytest Suite

---

## 1. Test Pyramid Architecture

To ensure fast execution, deterministic results, and $100\%$ repeatability without incurring cloud API costs or leaking rate limit quotas, the testing suite is structured according to the **Test Pyramid**:

```
                       / \
                      /   \
                     / E2E \       <-- Level 3: End-to-End API Integration Tests (5%)
                    /       \          FastAPI TestClient with in-memory MockTransport
                   /─────────\
                  / Contract  \    <-- Level 2: Component & Contract Tests (25%)
                 /  & Adapter  \       Platform Adapter payloads & MockTransport simulations
                /───────────────\
               /    Unit Tests   \ <-- Level 1: Unit Tests (70%)
              / (Fast, Isolated)  \    Validators, Regex parsing, Schema constraints, Log filters
             /─────────────────────\
```

---

## 2. In-Memory Mocking Strategy via `httpx.MockTransport` (Isolated Mocking)

Live network calls during automated CI/CD builds introduce severe anti-patterns:
- Flaky tests caused by third-party network packet drops.
- Rate limiting quota depletion during frequent automated runs.
- Exposure of real API credentials in CI worker logs.

### The Architectural Invariant:
**Automated test suites NEVER make live network connections to external platform servers.**
All outbound HTTP operations are intercepted in-memory using **`httpx.MockTransport`**:

```python
import httpx
import pytest

def create_mock_transport_handler(status_code: int = 200, response_json: dict = None):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=response_json or {})
    return httpx.MockTransport(handler)

@pytest.fixture
def mock_linkedin_client():
    mock_response = {"id": "urn:li:share:7123456789"}
    transport = create_mock_transport_handler(status_code=201, response_json=mock_response)
    return httpx.AsyncClient(transport=transport)
```

This guarantees that:
- 100+ tests execute in $<1.5\text{ seconds}$.
- Tests run identically offline, on local developer laptops, and in GitHub Actions CI runners.
- $100\%$ deterministic assertions on error status codes (401, 429, 500, timeout).

---

## 3. Code Coverage Mandate (Coverage Enforcement)

The test suite enforces a strict automated coverage threshold:
$$\text{Line Coverage} \ge 90\%$$
$$\text{Branch Coverage} \ge 85\%$$

Enforced via `pytest-cov`:
```powershell
pytest tests/ -v --cov=app --cov-report=term-missing --cov-fail-under=90
```
Any PR dropping below $90\%$ coverage is automatically failed by the CI pipeline.
