# Level 6: Testing Strategy & Test Suites — Performance & Load Testing Specification

**Document ID:** `DOC-TST-03-LOAD-TESTING`  
**Project:** `automated-posting`  
**Author:** Principal Software Architect
**Reviewer:** Staff Backend Engineering Lead
**Status:** APPROVED  
**Standard:** k6 Load Testing Framework, SEBI / SLA Performance Governance

---

## 1. Performance Objectives & Service Level Indicators (SLIs)

| Metric | Target SLA | Degraded Threshold | Failure Condition |
|---|---|---|---|
| **P95 Latency (Fast Path)** | $\le 2.0\text{ seconds}$ | $> 3.5\text{ seconds}$ | $> 10.0\text{ seconds}$ |
| **P99 Latency (Max Timeout)** | $\le 8.5\text{ seconds}$ | $> 9.5\text{ seconds}$ | $> 10.0\text{ seconds}$ |
| **Throughput (Concurrent Users)** | $\ge 50\text{ req/sec}$ | $< 25\text{ req/sec}$ | $< 10\text{ req/sec}$ |
| **Error Rate (Internal 5xx)** | $0.0\%$ | $> 0.1\%$ | $> 1.0\%$ |

---

## 2. Automated k6 Load Test Script (`tests/load/k6_posting_test.js`)

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 20 },  // Ramp-up to 20 virtual users
    { duration: '1m', target: 20 },   // Steady state
    { duration: '15s', target: 0 },   // Ramp-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<3000'], // 95% of requests must complete below 3s
    http_req_failed: ['rate<0.01'],    // Error rate must remain under 1%
  },
};

export default function () {
  const url = 'http://localhost:4000/posting';
  const payload = JSON.stringify({
    message: 'Scale multi-platform marketing automation with resilient async microservices! https://dxora.com',
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'X-Request-ID': `k6-${__VU}-${__ITER}`,
    },
    timeout: '10s',
  };

  const res = http.post(url, payload, params);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'has 5 platforms': (r) => JSON.parse(r.body).total_platforms === 5,
    'response time under 10s': (r) => r.timings.duration < 10000,
  });

  sleep(1);
}
```

---

## 3. Rate Limit Benchmark Protocol (ISSUE-008)

To benchmark rate limit behaviors:
1. Dispatch 100 burst requests within a 10-second window.
2. Confirm that platforms returning HTTP 429 are classified cleanly as `status: "failed"` with `error: "Rate limit exceeded"`.
3. Assert that zero 429 errors from upstream platforms cause the FastAPI server to crash or return unhandled 500 errors.
