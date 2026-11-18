# ADR-005: Platform Selection Rationale & Feasibility Analysis

**Status:** ACCEPTED  
**Date:** 2026-11-18  
**Author:** Principal Solutions Architect
**Reviewer:** Technical Architecture Review Board
**Governed Issue:** ISSUE-001, ISSUE-002, ISSUE-003, ISSUE-006, ISSUE-011  

---

## 1. Context & Problem Statement
The Practical Test requires identifying and integrating at least **5 suitable third-party platforms** through their official APIs. The platforms must support programmatic message publishing, provide public accessibility, have clear API documentation, and be practically feasible for a candidate evaluation environment.

## 2. Decision Drivers
- Free tier access without mandatory enterprise/paid subscription.
- Feasibility of authentication setup (avoiding multi-week manual business reviews).
- Programmatic API support for text and URL publishing.
- Diverse ecosystem representation (Professional, Developer, Blogging, Federated, Messaging).

## 3. Platform Candidates & Selected Suite

| Platform | Channel Type | API Standard | Auth Mechanism | Decision | Justification |
|---|---|---|---|---|---|
| **LinkedIn** | Professional Social | REST API | OAuth 2.0 UGC Post | **ACCEPTED** | #1 professional business network. High credibility. UGC Posts API (`POST /v2/ugcPosts`) supports public shares. |
| **Dev.to** | Developer Community | REST API (Forem) | Static API Key | **ACCEPTED** | Free public developer API. Instant API key generation. Content is indexed publicly. |
| **Hashnode** | Developer Blogging | GraphQL API | Personal Access Token | **ACCEPTED** | Modern GraphQL API (`https://gql.hashnode.com`). Free developer token. Highly relevant to tech publishing. |
| **Mastodon** | Federated Social | REST API | OAuth Bearer Token | **ACCEPTED** | Decentralized, open-source, resilient social protocol. Free instance registration on `mastodon.social`. Instant API token. |
| **Telegram** | Instant Messaging | Bot REST API | Bot Secret Token | **ACCEPTED** | Instant channel broadcasting via `@BotFather`. Free, reliable, millions of active community channels. |
| **Twitter / X** | Micro-Blogging | REST API v2 | OAuth 1.0a / 2.0 | **REJECTED** | X API v2 has discontinued free write access. Standard write tier requires $100+/month paid subscription. Unsuitable for practical test evaluation. |
| **Facebook Pages** | Social Media | Graph API | Page Access Token | **REJECTED** | Meta App Review requires multi-week manual compliance verification and company verification for `pages_manage_posts`. Not feasible in a 48-hour window. |
| **Medium** | Blogging | REST API | Integration Token | **REJECTED** | Medium deprecated its public integration token API in 2023. |

## 4. Decision Outcome
The 5 chosen platforms are **LinkedIn, Dev.to, Hashnode, Mastodon, and Telegram**. They represent a balanced portfolio across professional B2B, developer media, blogging platforms, decentralized networks, and instant messaging channels.
