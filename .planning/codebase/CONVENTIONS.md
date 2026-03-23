# Coding Conventions

**Analysis Date:** 2026-03-23

## Naming Patterns

**Files:**
- Python modules: snake_case (e.g., `market_data.py`, `price_cache.py`)
- Python test files: `test_*.py` (e.g., `test_portfolio.py`, `test_service.py`)
- TypeScript/React files: PascalCase for components (e.g., `TradeBar.tsx`, `Header.tsx`), camelCase for utilities (e.g., `usePrices.ts`, `api.ts`)
- Directories: lowercase with hyphens for multi-word names in frontend (e.g., `__tests__`), snake_case in backend (e.g., `app/market/`)

**Functions:**
- Python: snake_case (e.g., `get_cash_balance()`, `execute_trade()`, `_build_context()`)
- TypeScript: camelCase for regular functions and hooks (e.g., `fetchPortfolio()`, `usePrices()`, `handleTrade()`)
- Python private helpers: prefixed with underscore (e.g., `_now()`, `_row_to_dict()`, `_build_context()`)

**Variables:**
- Python: snake_case consistently (e.g., `current_price`, `total_value`, `unrealized_pnl`)
- TypeScript: camelCase (e.g., `activeTicker`, `selectedTicker`, `connectionStatus`)
- Constants in Python: UPPER_SNAKE_CASE (e.g., `DEFAULT_TICKERS`, `MODEL`, `SYSTEM_PROMPT`)
- React state: camelCase with semantic names (e.g., `portfolio`, `watchlist`, `connectionStatus`)

**Types:**
- Python Pydantic models: PascalCase (e.g., `PriceUpdate`, `TradeRequest`, `LlmResponse`)
- TypeScript interfaces: PascalCase (e.g., `UsePricesResult`, `TradeBarProps`, `ChatResponse`)
- Database column names: snake_case (e.g., `cash_balance`, `avg_cost`, `previous_price`)

## Code Style

**Formatting:**
- Python: Ruff formatter with line length of 100 characters
- TypeScript: ESLint with Next.js configuration (strict type checking enabled)
- Indentation: 4 spaces (Python), 2 spaces (TypeScript)

**Linting:**
- Python: Ruff with rule set E, F, I, N, W; E501 (line too long) ignored
- TypeScript: ESLint with eslint-config-next (web vitals + TypeScript support)

**Docstrings (Python):**
- Module-level docstring required on Python files
- Function docstrings: brief description of purpose, parameters, return value (concise style)
- Example from `cache.py`: "Thread-safe in-memory cache of the latest price for each ticker."

**JSDoc/TSDoc (TypeScript):**
- Component interface props typed via TypeScript interfaces (e.g., `TradeBarProps`)
- No excessive comments; type signatures serve as documentation

## Import Organization

**Order (Python):**
1. `__future__` imports (e.g., `from __future__ import annotations`)
2. Standard library imports (e.g., `import os`, `from pathlib import Path`)
3. Third-party imports (e.g., `from fastapi import FastAPI`, `from pydantic import BaseModel`)
4. Local app imports (e.g., `from app.db import get_cash_balance`)

**Order (TypeScript):**
1. React/library imports (e.g., `import { useState, useEffect } from "react"`)
2. Internal type imports (e.g., `import type { Portfolio } from "@/lib/types"`)
3. Utility/API imports (e.g., `from "@/lib/api"`, `from "@/components/Header"`)
4. Hooks last (e.g., `from "@/hooks/usePrices"`)

**Path Aliases:**
- TypeScript: `@/` resolves to project root (configured in `tsconfig.json`)
- Used consistently across frontend for imports: `@/components/`, `@/lib/`, `@/hooks/`

## Error Handling

**Python Patterns:**
- Use FastAPI `HTTPException` for API errors with descriptive status codes and detail messages
  - Example: `raise HTTPException(status_code=400, detail="Insufficient cash. Need ${cost:.2f}, have ${cash:.2f}")`
- Database operations wrapped in try/except to catch integrity constraint violations
  - Example from `watchlist.py`: catches duplicate entry on UNIQUE constraint, returns 409 Conflict
- LLM service catches parsing errors without raising 500; returns 200 with error details in response
- Background tasks use try/except with logging on exception, never propagate errors to crash app
  - Example from `main.py`: `_snapshot_loop` catches exceptions and logs them

**TypeScript Patterns:**
- Async API functions use try/catch and throw `Error` with descriptive message
  - Example: `if (!res.ok) throw new Error("Failed to fetch portfolio")`
- React event handlers catch errors and set status state (e.g., `TradeBar.tsx` sets error status)
- Silent failures allowed in periodic polling (`page.tsx` retries on next interval if fetch fails)
- Unknown error type guarded: `err instanceof Error ? err.message : "Trade failed"`

## Comments

**When to Comment (Python):**
- Module-level docstring on all files
- Function docstrings for public APIs and non-obvious internal functions
- Inline comments only for complex logic (e.g., "Monotonically increasing; bumped on every update")
- No obvious comments ("increment counter", "get the user") — let code speak for itself

**When to Comment (TypeScript):**
- Component JSDoc via TypeScript interface documentation (props types)
- Minimal inline comments; type signatures and clear naming preferred
- Example from `usePrices.ts`: function purpose clear from name and return type

## Function Design

**Size (Python):**
- Small, single-responsibility functions preferred (e.g., `_now()` for timestamp, `_row_to_dict()` for conversion)
- Routes typically 20-40 lines (e.g., `get_portfolio()` in `portfolio.py`)
- Service functions break into helpers (e.g., `_build_context()`, `_build_messages()`, `_execute_actions()`)

**Size (TypeScript):**
- React components 50-100 lines preferred (e.g., `TradeBar.tsx` ~77 lines)
- Custom hooks concise (e.g., `usePrices` hook ~55 lines)
- Handlers extracted to named functions (e.g., `handleTrade()` in `TradeBar.tsx`)

**Parameters:**
- Python: Pass explicit parameters; avoid relying on module state when possible
- TypeScript: Use destructuring for props (e.g., `{ onTradeExecuted, selectedTicker }`)
- Both: Pydantic `BaseModel` or TypeScript interfaces for complex request bodies

**Return Values:**
- Python: Explicit return types via type hints (e.g., `-> dict`, `-> float | None`)
- TypeScript: Explicit return types for non-inferrable cases (e.g., `UsePricesResult` interface)
- Consistent JSON dict return format from API endpoints

## Module Design

**Exports (Python):**
- Package `__init__.py` re-exports key public symbols
  - Example: `app/market/__init__.py` exports `PriceCache`, `PriceUpdate`, `MarketDataSource`
- Private module-level symbols prefixed with `_`
- Dataclasses frozen and immutable where appropriate (e.g., `PriceUpdate`)

**Exports (TypeScript):**
- Default export for React components (e.g., `export default function TradeBar(...)`)
- Named exports for utilities and types (e.g., `export interface Portfolio`, `export async function fetchPortfolio()`)
- No barrel files outside of type definitions (`app/types/index.ts` re-exports types)

**Conciseness Principle:**
- Short modules encouraged (e.g., `models.py` contains only dataclasses, `cache.py` contains only `PriceCache`)
- Service layer orchestrates across modules without duplicating logic
- Avoid "god classes" — split large services into focused, testable units

---

*Convention analysis: 2026-03-23*
