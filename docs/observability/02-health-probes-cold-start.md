# Level 5: Observability, Telemetry & SRE Architecture — Health Probes & Cold-Start Strategy

**Document ID:** `DOC-OBS-02-HEALTH-PROBES`  
**Project:** `automated-posting`  
**Author:** Principal Software Architect
**Reviewer:** Staff Backend Engineering Lead
**Status:** APPROVED  
**Standard:** Kubernetes Pod Lifecycle & Cloud-Native Health Checking

---

## 1. Dual Health Check Architecture

To support modern container orchestrators (Kubernetes, Docker Swarm, Cloud Run) and edge load balancers, the application exposes dual health endpoints:

### 1.1 Liveness Probe (`GET /health`)
- **Intent:** Answers: *"Is the Python interpreter process alive and responsive to HTTP traffic?"*
- **Behavior:** Lightweight, immediate execution. Touches zero database connections or external network APIs.
- **HTTP Response:** `200 OK`
```json
{
  "status": "ok"
}
```

### 1.2 Readiness Probe (`GET /ready`)
- **Intent:** Answers: *"Is the microservice configured and ready to accept live broadcast traffic?"*
- **Behavior:** Verifies that environment variables are loaded and evaluates which platform adapters are configured.
- **HTTP Response:** `200 OK`
```json
{
  "status": "ready",
  "platforms_configured": 5,
  "adapters": ["LinkedIn", "Dev.to", "Hashnode", "Mastodon", "Telegram"]
}
```

---

## 2. Cold-Start Mitigation for Free Tier PaaS Hosting (ISSUE-012)

### The Cloud Problem:
PaaS providers like Render.com and Railway automatically suspend free-tier web services after 15 minutes of inbound inactivity to save compute resources. When a reviewer or client clicks the Live Demo link after a period of dormancy, the container experiences a **Cold Start**, taking 30 to 50 seconds to boot the Linux image and initialize the Python runtime.

### The Mitigation Plan:
1. **Zero-Latency Ingress:** The root route `GET /` and health route `GET /health` require no external network calls and respond in $<10\text{ms}$ once booted.
2. **Automated Ping Keepalive Script:** We provide a simple keepalive cron configuration (runnable via GitHub Actions or free monitoring tools like UptimeRobot / cron-job.org) that sends an HTTP GET to `/health` every 14 minutes between 18 Nov and 22 Nov 2026.
3. **Transparent Reviewer Documentation:** The root `README.md` includes a prominent note explaining that if the instance has been idle, the first request may take up to 45 seconds to spin up the container, after which all subsequent requests respond in sub-2 seconds.
