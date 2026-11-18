# Communication Diagram — Automated Multi-Platform Posting System

```mermaid
graph LR
    Client[1: Client] -->|1: POST /posting| Router[2: Main Router]
    Router -->|1.1: validate()| Validator[3: Validators]
    Router -->|1.2: post_to_all()| Service[4: PostingService]

    Service -->|1.2.1: post() [async]| A1[5.1: LinkedIn Adapter]
    Service -->|1.2.2: post() [async]| A2[5.2: Dev.to Adapter]
    Service -->|1.2.3: post() [async]| A3[5.3: Hashnode Adapter]
    Service -->|1.2.4: post() [async]| A4[5.4: Mastodon Adapter]
    Service -->|1.2.5: post() [async]| A5[5.5: Telegram Adapter]

    A1 -->|1.2.1.1: Outbound HTTP| E1[(LinkedIn Cloud)]
    A2 -->|1.2.2.1: Outbound HTTP| E2[(Dev.to Cloud)]
    A3 -->|1.2.3.1: Outbound GraphQL| E3[(Hashnode Cloud)]
    A4 -->|1.2.4.1: Outbound HTTP| E4[(Mastodon Cloud)]
    A5 -->|1.2.5.1: Outbound HTTP| E5[(Telegram Cloud)]

    Service -->|1.3: filter_logs()| Logger[6: SanitizedLogger]
```
