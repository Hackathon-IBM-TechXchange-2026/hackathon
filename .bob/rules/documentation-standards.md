# Documentation Standards

## Guidelines
- **Sync with Code**: Every change in method signature, payload structure, or error response must be reflected immediately in `API.md` and `ARCHITECTURE.md`.
- **OpenAPI & Markdown Format**: Keep parameter types, required fields, and response examples formatted in clean Markdown tables and OpenAPI/Swagger compliant JSON schemas.
- **Architectural Traceability**: When new components, adapters, or service layers are added, update the Mermaid sequence and component diagrams in `ARCHITECTURE.md`.
- **Targeted Updates**: Avoid modifying unrelated sections of documentation files to minimize Git diff clutter.

