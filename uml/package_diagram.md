# Package Diagram — Automated Multi-Platform Posting System

**Document ID:** `UML-PKG-01`  
**Architecture Standard:** Clean Decoupled Microservice Layering  
**Author:** Principal Software Architect  
**Status:** APPROVED  

```mermaid
graph TD
    subgraph RootPackage [app]
        subgraph MainPkg [app.main]
            MainApp["main.py: FastAPI Entrypoint & Lifespan"]
            GlobalHandlers["Global RFC 7807 Exception Handlers"]
        end

        subgraph CorePkg [app.core]
            Constants["constants.py: ServiceMessage, ValidationMessage, Api & Platform Constants"]
            Config["config.py: Settings (pydantic-settings)"]
            Exceptions["exceptions.py: ApplicationException Hierarchy"]
            Logging["logging.py: SensitiveDataFilter & Structured JSON Logger"]
        end

        subgraph RoutersPkg [app.routers]
            PostingRouter["posting.py: POST /posting Ingress Controller"]
            HealthRouter["health.py: GET /health & GET /ready Probes"]
        end

        subgraph ModelsPkg [app.models]
            subgraph FormsPkg [app.models.forms]
                PostingForm["posting_form.py: PostingForm (7-Stage Validation Pipeline)"]
            end
            subgraph DTOsPkg [app.models.dtos]
                PostingDTO["posting_dto.py: PostingResponseDto & TelemetryDto"]
                PlatformDTO["platform_dto.py: PlatformResultDto"]
                ProblemDTO["problem_dto.py: ProblemDetailsDto (RFC 7807)"]
                ApiResponseDTO["api_response.py: ApiResponseDto Generic Envelope"]
            end
        end

        subgraph ServicesPkg [app.services]
            ServiceContract["posting_service.py: PostingService (Interface)"]
            ServiceImpl["posting_service.py: PostingServiceImpl (Bulkhead Orchestrator)"]
            ServiceHelper["posting_helper.py: PostingServiceHelper (DTO Mapping & Aggregation)"]
        end

        subgraph PlatformsPkg [app.platforms]
            BasePort["base.py: BasePlatformAdapter (Abstract Port)"]
            RegistryPkg["registry.py: AdapterRegistry (Factory)"]
            LinkedInPkg["linkedin.py: LinkedInAdapter"]
            DevToPkg["devto.py: DevToAdapter"]
            HashnodePkg["hashnode.py: HashnodeAdapter"]
            MastodonPkg["mastodon.py: MastodonAdapter"]
            TelegramPkg["telegram.py: TelegramAdapter"]
        end
    end

    MainPkg --> RoutersPkg
    MainPkg --> CorePkg
    MainPkg --> ServicesPkg
    MainPkg --> PlatformsPkg

    RoutersPkg --> FormsPkg
    RoutersPkg --> ServicesPkg
    RoutersPkg --> DTOsPkg
    RoutersPkg --> CorePkg

    ServicesPkg --> PlatformsPkg
    ServicesPkg --> DTOsPkg
    ServicesPkg --> CorePkg
    ServiceImpl --|> ServiceHelper
    ServiceImpl ..|> ServiceContract

    PlatformsPkg --> DTOsPkg
    PlatformsPkg --> CorePkg
    RegistryPkg ..> BasePort : instantiates
    BasePort <|-- LinkedInPkg
    BasePort <|-- DevToPkg
    BasePort <|-- HashnodePkg
    BasePort <|-- MastodonPkg
    BasePort <|-- TelegramPkg

    FormsPkg --> CorePkg
```
