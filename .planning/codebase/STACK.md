# Technology Stack

**Analysis Date:** 2026-03-23

## Languages

**Primary:**
- TypeScript 5.x - Frontend (React, Next.js)
- Python 3.12 - Backend (FastAPI, market data, LLM integration)

**Secondary:**
- JavaScript - Frontend tooling and config
- Shell - Docker build and start/stop scripts

## Runtime

**Environment:**
- Node.js 20 (slim) - Frontend build stage
- Python 3.12 (slim) - Backend runtime
- Docker - Containerized deployment

**Package Manager:**
- npm (Node.js) - Frontend dependency management
- uv - Python dependency management (modern replacement for pip/virtualenv)
  - Lockfile: `backend/uv.lock` (present, frozen)

## Frameworks

**Core:**
- **Next.js 16.1.6** - React framework with static export (`output: 'export'`)
- **FastAPI 0.128.7** - Python async web framework for backend API and static file serving
- **React 19.2.3** - Frontend UI library

**UI/Charting:**
- **Tailwind CSS 4.x** - Utility-first CSS framework (dark theme)
- **Lightweight Charts 5.1.0** - Canvas-based financial charting (price over time)
- **Recharts 3.7.0** - React charting library (portfolio heatmap, P&L tracking)

**Server/Async:**
- **Uvicorn 0.40.0** - ASGI server for FastAPI
- **aiosqlite 0.22.1** - Async SQLite client for non-blocking database operations

**Testing:**
- **Jest 30.2.0** - JavaScript test runner (frontend)
- **pytest 9.0.2** - Python test framework (backend)
- **pytest-asyncio 0.24.0** - Async support for pytest
- **pytest-cov 5.0.0** - Coverage reporting for pytest
- **React Testing Library 16.3.2** - Component testing utilities

**Build/Dev:**
- **Ruff 0.7.0** - Fast Python linter and formatter
- **ESLint 9.x** - JavaScript linter
- **ts-jest 29.4.6** - TypeScript support for Jest

## Key Dependencies

**Critical - Market Data:**
- **numpy 2.4.2** - Numerical computing; used by simulator for geometric Brownian motion price generation
- **massive 2.2.0** - Polygon.io API client for real market data (REST API polling, rate-limited)

**Critical - LLM Integration:**
- **litellm 1.81.10** - LLM abstraction layer; routes to OpenRouter with Cerebras inference provider
- Structured output support via Pydantic BaseModel

**Infrastructure/Utilities:**
- **rich 14.3.2** - Terminal formatting and progress bars (logging, CLI tools)

**Development:**
- **@tailwindcss/postcss 4.x** - PostCSS plugin for Tailwind
- **@testing-library/jest-dom 6.9.1** - DOM matchers for Jest
- **@types/node, @types/react, @types/react-dom** - TypeScript type definitions

## Configuration

**Environment:**
- **`.env` file** (at project root, gitignored)
  - `OPENROUTER_API_KEY` - Required for LLM chat (OpenRouter API key)
  - `MASSIVE_API_KEY` - Optional for real market data (Polygon.io); simulator used if empty
  - `LLM_MOCK=true|false` - Enable mock LLM responses for testing (defaults to "false")
- **`.env.example`** - Template with documented variables

**Backend Configuration:**
- `FINALLY_DB_PATH` - Optional override for SQLite database location (defaults to `db/finally.db`)

**Build:**
- `frontend/tsconfig.json` - TypeScript compiler config (ES2017 target, strict mode, bundler resolution)
- `frontend/next.config.ts` - Next.js config with static export enabled, image optimization disabled
- `backend/pyproject.toml` - Python project metadata, dependencies, pytest/ruff/coverage config
- `Dockerfile` - Multi-stage build (Node 20 → Python 3.12)
- `docker-compose.yml` - Service definition with volume mount for SQLite persistence

## Database

**SQLite 3** - Single-file relational database
- File: `db/finally.db` (volume-mounted in Docker)
- Connection: `aiosqlite` with async support
- Pragmas: WAL mode, foreign keys enabled
- Lazy initialization: tables created on first app startup if missing
- Seeding: default user ($10,000 cash), default watchlist (10 tickers)

## Platform Requirements

**Development:**
- Docker and Docker CLI (for local containerized development)
- Node.js 20.x
- Python 3.12
- uv package manager
- bash/zsh shell (for start/stop scripts)

**Production:**
- Docker (container runtime required)
- Any container orchestration platform (AWS App Runner, Render, etc.)
- 8000 port exposed for HTTP traffic
- Volume mount at `/app/db` for SQLite persistence

---

*Stack analysis: 2026-03-23*
