# ADR-008: Deployment Topology & Production Hosting (Render.com + Docker)

**Status:** ACCEPTED  
**Date:** 2026-11-18  
**Author:** Principal DevOps & SRE Engineer
**Reviewer:** Operations Review Board
**Governed Issue:** ISSUE-012 (Render.com Free Tier Cold Starts)  

---

## 1. Context & Problem Statement
The Practical Test requires deploying the completed FastAPI application on a publicly accessible server, providing a **Live Demo URL**, and sharing the `/docs` documentation link for verification. The hosting solution must support Python 3.10+, environment variables for secrets, HTTPS termination, and public accessibility.

## 2. Decision Drivers
- Zero deployment cost (free tier availability).
- Automated git-push continuous deployment.
- Native HTTPS SSL certificate provisioning.
- Docker containerization support for reproducibility.
- Predictable uptime during reviewer evaluation.

## 3. Considered Options
1. **Render.com Web Service (Docker / Native Python runtime)**
2. **Railway.app**
3. **AWS EC2 / GCP Cloud Run (Free Tier)**

## 4. Decision Outcome
**Chosen Option:** **Render.com Web Service via Multi-Stage Dockerfile**

### Deployment Topology:
```
[ Developer Git Push: main ] ──► [ GitHub Repository: automated-posting ]
                                              │
                                              ▼
                                 [ Render.com Webhook ]
                                              │
                                 [ Multi-Stage Docker Build ]
                                 (python:3.11-slim, non-root appuser)
                                              │
                                 [ Production Container Run ]
                                 (Uvicorn on port 10000 -> HTTPS Termination)
                                              │
                                 [ Public Live URL ]
                                 https://automated-posting-dxora.onrender.com
```

### Cold-Start Mitigation Strategy (Addressing ISSUE-012):
Render's free tier spins down idle web services after 15 minutes of inactivity. When a reviewer hits the endpoint, initial spin-up can take 30-50 seconds.
**Mitigations:**
1. Expose a zero-overhead `GET /health` endpoint that returns immediately without touching platform APIs.
2. Provide a lightweight keepalive cron script (using GitHub Actions / UptimeRobot) to ping `/health` every 14 minutes during the evaluation window (18 Nov to 22 Nov).
3. Document cold-start behavior clearly in the root README so evaluators are aware that the first request may take a moment to wake the instance.
