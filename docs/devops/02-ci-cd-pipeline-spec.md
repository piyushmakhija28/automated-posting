# Level 7: DevOps & Container Architecture — CI/CD Pipeline Specification

**Document ID:** `DOC-OPS-02-CICD-PIPELINE`  
**Project:** `automated-posting`  
**Author:** Principal Software Architect
**Reviewer:** Staff Backend Engineering Lead
**Status:** APPROVED  
**Standard:** GitHub Actions CI/CD Best Practices, DevSecOps Automated Quality Gates

---

## 1. Automated Continuous Integration Workflow (`.github/workflows/ci.yml`)

The continuous integration pipeline triggers automatically on every pull request and push to the `main` branch. It enforces 5 sequential automated gates:

```
[ Push to main / PR ]
         │
         ▼
[ Step 1: Linting & Code Formatting (Ruff + Black) ]
         │
         ▼
[ Step 2: Static Type Checking (Mypy --strict) ]
         │
         ▼
[ Step 3: Security SAST Vulnerability Scan (Bandit) ]
         │
         ▼
[ Step 4: Automated Test Execution & Coverage Gate (Pytest >= 90%) ]
         │
         ▼
[ Step 5: Docker Container Build & Health Validation ]
         │
         ▼
[ Automated Deploy Trigger: Render.com Webhook ]
```

---

## 2. GitHub Actions Workflow Configuration Specification

```yaml
name: CI/CD Pipeline - Quality & Security Gates

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  validate-and-test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]

    steps:
      - name: Checkout Source Code
        uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install ruff black mypy bandit pytest pytest-asyncio pytest-cov

      - name: Gate 1 - Code Formatting & Linting (Ruff & Black)
        run: |
          ruff check app/ tests/
          black --check app/ tests/

      - name: Gate 2 - Strict Static Type Analysis (Mypy)
        run: |
          mypy app/ --strict

      - name: Gate 3 - Security Vulnerability Scan (Bandit SAST)
        run: |
          bandit -r app/ -ll

      - name: Gate 4 - Automated Test Execution & Coverage (>= 90%)
        run: |
          pytest tests/ -v --cov=app --cov-report=term-missing --cov-fail-under=90

      - name: Gate 5 - Verify Docker Build
        run: |
          docker build -t automated-posting:test .
```
