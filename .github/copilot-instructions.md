# GitHub Copilot Instructions for BRAiN Project

## Project Context
BRAiN is a bio-inspired Multi-Agent System implementing Myzelkapitalismus philosophy.

## Architecture Principles
- **Modular Design**: All features as independent modules in \pp/modules/\
- **Event-Driven**: Use EventBus for inter-module communication
- **Registry Pattern**: ModuleRegistry for dynamic module loading
- **Bio-Inspired**: Cortex (decision), Limbic (emotion), Stem (execution)

## Code Style
- Python: FastAPI async/await, type hints, Pydantic models
- TypeScript: Next.js 14 App Router, Server Components
- Comments: German for business logic, English for technical code

## Key Modules
- **karma**: Reputation & trust scoring (Myzelkapitalismus)
- **dna**: Agent inheritance & evolution
- **immune**: Security & threat detection
- **missions**: Task orchestration
- **credits**: Resource economy

## Naming Conventions
- Modules: lowercase (e.g., \karma\, \dna\)
- Classes: PascalCase (e.g., \KarmaModule\)
- Functions: snake_case (e.g., \calculate_karma\)
- Events: UPPER_SNAKE_CASE (e.g., \MISSION_COMPLETED\)

## Testing
- Unit tests in \	ests/\ mirror \pp/\ structure
- Use pytest with async support
- Mock external APIs (Anthropic, Qdrant)

## Docker
- Multi-stage builds for production
- Separate containers for backend, frontend, workers
- Use docker-compose for local dev, Kubernetes for prod

## Security
- Never commit API keys
- Use .env.example for templates
- Immune module validates all external inputs

## Philosophy: Myzelkapitalismus
- Cooperation over competition
- Decentralized decision-making
- Resource sharing via credits
- Reputation-based trust (karma)
