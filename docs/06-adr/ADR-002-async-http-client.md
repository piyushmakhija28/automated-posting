# ADR-002: Asynchronous HTTP Client Selection (HTTPX vs Requests vs aiohttp)

**Status:** ACCEPTED  
**Date:** 2026-11-18  
**Author:** Principal Solutions Architect
**Reviewer:** Technical Architecture Review Board
**Governed Issue:** ISSUE-004 (Blocking I/O in Async Loop)  

---

## 1. Context & Problem Statement
Our application must make parallel outbound HTTP/HTTPS calls to 5+ distinct external APIs (LinkedIn, Dev.to, Hashnode, Mastodon, Telegram). Making synchronous HTTP calls inside an async FastAPI handler blocks the single-threaded event loop, effectively serializing all incoming and outgoing requests and degrading performance.

## 2. Decision Drivers
- True non-blocking asynchronous I/O (`async`/`await`).
- Standard, modern HTTP/1.1 and HTTP/2 transport support.
- Connection pooling and keep-alive reuse across concurrent requests.
- First-class in-memory mocking capability for deterministic unit and integration testing without live network calls.
- Intuitive Requests-compatible API syntax.

## 3. Considered Options
1. **HTTPX (`httpx.AsyncClient`)**
2. **Requests (`requests.get`, `requests.post`)**
3. **aiohttp (`aiohttp.ClientSession`)**

## 4. Decision Outcome
**Chosen Option:** **HTTPX (`httpx.AsyncClient`)**

### Positive Consequences:
- **Event Loop Safety:** `httpx.AsyncClient` utilizes async socket selectors, ensuring that when an adapter waits on network responses, the Python event loop immediately switches to process other adapters or incoming requests.
- **Mock Transport Primitives:** HTTPX provides `httpx.MockTransport`, allowing our test suite (`tests/test_posting.py`) to mock network responses in-memory with zero monkey-patching or flaky socket servers.
- **Familiar Ergonomics:** Clean syntax identical to Requests (`client.post(url, json=..., headers=...)`).
- **Context Manager Support:** Easy lifespan management via `async with httpx.AsyncClient() as client:`.

### Negative Consequences:
- Client session pooling must be managed cleanly to prevent unclosed connection warnings.

---

## 5. Pros and Cons of Alternatives

### Requests
- *Pros:* Industry standard, ubiquitous documentation.
- *Cons:* **STRICTLY BANNED in async context.** Requests is completely synchronous and blocking. Calling `requests.post()` in a coroutine halts the entire worker thread until the external server answers, causing severe latency spikes (ISSUE-004).

### aiohttp
- *Pros:* Very fast, mature async client.
- *Cons:* More verbose syntax (e.g. requires `async with resp:` and `await resp.json()`); testing mock utilities are clunkier than HTTPX's elegant `MockTransport`.
