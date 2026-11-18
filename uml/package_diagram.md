# Package Diagram — Automated Multi-Platform Posting System

```mermaid
graph TD
    subgraph RootPackage [app]
        subgraph MainPkg [app.main]
            MainApp[main.py: FastAPI Entrypoint]
            Lifespan[Lifespan Context Manager]
        end

        subgraph ExceptionsPkg [app.exceptions]
            DomainExc[exceptions.py: PostingAppException Hierarchy]
        end

        subgraph SchemasPkg [app.schemas]
            ReqSchemas[PostRequest: 7-Stage Sanitizer]
            RespSchemas[PostResponse, PlatformResult, ProblemDetails]
        end

        subgraph ConfigPkg [app.config]
            Settings[Settings: Pydantic-Settings]
        end

        subgraph UtilsPkg [app.utils]
            Validators[validators.py: URL, NFKC, SSRF Screening]
            Logger[logger.py: SensitiveDataFilter Token Masker]
        end

        subgraph ServicesPkg [app.services]
            PostingService[posting_service.py: PostingService Orchestrator]
        end

        subgraph PlatformsPkg [app.platforms]
            BasePort[base.py: BasePlatform Port]
            RegistryPkg[registry.py: AdapterRegistry Factory]
            LinkedInPkg[linkedin.py: LinkedInPlatform]
            DevToPkg[devto.py: DevToPlatform]
            HashnodePkg[hashnode.py: HashnodePlatform]
            MastodonPkg[mastodon.py: MastodonPlatform]
            TelegramPkg[telegram.py: TelegramPlatform]
        end
    end

    MainPkg --> SchemasPkg
    MainPkg --> ServicesPkg
    MainPkg --> ConfigPkg
    MainPkg --> UtilsPkg
    MainPkg --> ExceptionsPkg

    ServicesPkg --> PlatformsPkg
    ServicesPkg --> SchemasPkg
    ServicesPkg --> ExceptionsPkg

    PlatformsPkg --> SchemasPkg
    PlatformsPkg --> UtilsPkg
    PlatformsPkg --> ConfigPkg
    PlatformsPkg --> BasePort
    PlatformsPkg --> ExceptionsPkg

    RegistryPkg ..> BasePort : instantiates
    BasePort <|-- LinkedInPkg
    BasePort <|-- DevToPkg
    BasePort <|-- HashnodePkg
    BasePort <|-- MastodonPkg
    BasePort <|-- TelegramPkg
```
