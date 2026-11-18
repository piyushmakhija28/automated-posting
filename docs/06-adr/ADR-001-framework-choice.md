# ADR-001: Web Framework Selection (FastAPI vs Flask vs Django REST)

**Status:** ACCEPTED  
**Date:** 2026-11-18  
**Author:** Principal Solutions Architect
**Reviewer:** Technical Architecture Review Board
**Deciders:** Technical Architecture Board  

---

## 1. Context & Problem Statement
We need to develop an asynchronous REST API service that handles concurrent fan-out network operations, enforces strict schema validation on incoming JSON payloads, auto-generates interactive API documentation (OpenAPI/Swagger), and runs with minimal memory footprint.

## 2. Decision Drivers
- Native async/await support on Python's event loop (ASGI standard).
- Built-in data validation and serialization with zero boilerplate.
- Automated OpenAPI 3.1.0 and interactive Swagger UI generation.
- High request throughput and low baseline latency.
- Strict type-hint enforcement compatible with Python 3.10+.

## 3. Considered Options
1. **FastAPI (with Uvicorn ASGI)**
2. **Flask (with Gunicorn/gevent)**
3. **Django REST Framework (DRF)**

## 4. Decision Outcome
**Chosen Option:** **FastAPI (with Uvicorn ASGI)**

### Positive Consequences:
- **Asynchronous Primitives:** Built on Starlette, FastAPI natively supports async request handlers, allowing non-blocking I/O operations with `asyncio.gather` without spawning expensive OS threads.
- **Pydantic v2 Integration:** Out-of-the-box data parsing, character bounding, regex validation, and error serialization.
- **Auto-Documentation:** Automatic `/docs` (Swagger UI) and `/redoc` rendering without manual documentation maintenance.
- **Performance:** Ranked among the fastest Python web frameworks (benchmarked near NodeJS and Go).

### Negative Consequences:
- Requires developers to understand async/await paradigms and avoid accidental synchronous blocking calls.

---

## 5. Pros and Cons of Alternatives

### Flask
- *Pros:* Simple, mature ecosystem, large library of extensions.
- *Cons:* Synchronous by default (WSGI). Adding async support via `quart` or Flask 2.0 async views still carries legacy synchronous middleware bottlenecks; lacks native schema validation (requires external Marshmallow or Webargs).

### Django REST Framework (DRF)
- *Pros:* Batteries-included ORM, admin panel, built-in authentication tables.
- *Cons:* Extremely heavyweight for a microservice with a single `/posting` endpoint; heavy relational database coupling; significant memory footprint and slower startup times.
