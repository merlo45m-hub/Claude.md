# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workspace Overview

Multi-project workspace at `/root/`. Each project is self-contained in its own directory.

| Project | Path | Stack | Description |
|---------|------|-------|-------------|
| **Hermes Agent** | `/root/hermes-agent/` | Python (uv) | Self-improving AI agent by Nous Research. CLI, multi-platform gateway, skills, tools. |
| **OmniRoute** | `/root/OmniRoute/` | Next.js 16 | AI proxy/router — 237 LLM providers, auto-fallback, MCP/A2A, desktop, PWA. |
| **AI Crypto Bot** | `/root/ai-crypto-bot/` | Python (uv) | AI-powered crypto trading bot. ccxt, Pydantic, SQLite, paper trading. |
| **Parseltongue** | `/root/parseltongue/` | React/TypeScript | Browser extension for text conversion & tokenization visualization. |
| **AI Stock Trader** | `/root/ai_stock_trader/` | Python/Flask | Stock trading bot with real-time dashboard, WebSocket, SQLite. |
| **Hermes WebUI** | `/root/hermes-webui/` | Python | Web UI for Hermes Agent. |
| **GBrain** | `/root/gbrain/` | TypeScript (Bun) | Postgres-native personal knowledge brain with hybrid RAG search. |
| **Atomic** | `/root/atomic/` | Rust/Tauri | Personal knowledge base. Cargo workspace with core, server, cloud, MCP crates. |
| **Options Bot** | `/root/projects/trading/options-bot/` | Python | Options trading bot with strategy engine, risk management. |
| **Market Bot** | `/root/projects/trading/market-bot/` | Python | Market analysis bot with scanner, signals, trader modules. |

## Project-Specific Commands

### Hermes Agent (`/root/hermes-agent/`)
```bash
cd /root/hermes-agent
uv run hermes              # Start chatting
uv run hermes model        # Switch LLM provider/model
uv run hermes gateway      # Start gateway (Telegram, Discord, etc.)
uv run hermes cron         # Manage scheduled automations
uv run pytest tests/       # Run tests
uv run pytest tests/test_file.py -k "test_name"  # Single test
uv run ruff check .        # Lint
uv run mypy .              # Type check
```

### OmniRoute (`/root/OmniRoute/`)
```bash
cd /root/OmniRoute
npm install                # Install deps
npm run dev                # Dev server at localhost:20128
npm run build              # Production build
npm run lint               # ESLint
npm run test:coverage      # Unit tests + coverage gate
```
See `/root/OmniRoute/CLAUDE.md` for full details.

### AI Crypto Bot (`/root/ai-crypto-bot/`)
```bash
cd /root/ai-crypto-bot
uv run python -m src.main       # Run bot
uv run pytest tests/             # Run tests
uv run ruff check src/           # Lint
uv run mypy src/                 # Type check
```

### Parseltongue (`/root/parseltongue/`)
```bash
cd /root/parseltongue
npm run build              # Webpack production build
npm run watch              # Dev watch mode
npm test                   # React test runner
```

### AI Stock Trader (`/root/ai_stock_trader/`)
```bash
cd /root/ai_stock_trader
python dashboard.py        # Start web dashboard (Flask-SocketIO)
python debug.py            # Debug tools
```

### GBrain (`/root/gbrain/`)
```bash
cd /root/gbrain
bun run <script>           # Run TypeScript scripts
```
Postgres-native RAG knowledge brain. Core engine at `src/core/engine.ts`, embedding at `src/core/embedding.ts`.

### Atomic (`/root/atomic/`)
```bash
cd /root/atomic
cargo build                # Build all crates
cargo run -p atomic-server  # Run server
cargo test                 # Run tests
```
Cargo workspace: `atomic-core`, `atomic-server`, `atomic-cloud`, `mcp-bridge`, `atomic-bench`.

### Options Bot (`/root/projects/trading/options-bot/`)
```bash
cd /root/projects/trading/options-bot
python main.py
```

### Market Bot (`/root/projects/trading/market-bot/`)
```bash
cd /root/projects/trading/market-bot
python main.py
```

## Architecture Notes

### Hermes Agent
Core agent framework. Key modules:
- `cli.py` — Main CLI entry point
- `run_agent.py` — Agent runtime
- `hermes_state.py` — State management
- `agent/` — Core agent logic (providers, adapters, runtime)
- `tools/` — Tool implementations (browser, code execution, computer use, etc.)
- `skills/` — Agent skills organized by domain (software-dev, research, email, etc.)
- `gateway/` — Multi-platform gateway (Telegram, Discord, Slack, etc.)
- `providers/` — LLM provider integrations

### OmniRoute (`/root/OmniRoute/`)
Next.js 16 AI proxy/router. See `/root/OmniRoute/CLAUDE.md` for full details.
- `src/app/` — Next.js App Router pages (dashboard, API routes, auth, docs)
- `src/server/` — Server-side (auth, CORS, WebSocket, origin handling)
- `src/lib/` — Core libraries (A2A, ACP, auth, caching, CLI, MCP, models, SSE)
- `src/mitm/` — MITM proxy layer
- `src/models/` — LLM model definitions and routing
- `src/store/` — State management

### AI Crypto Bot (`/root/ai-crypto-bot/`)
- `src/main.py` — Entry point
- `src/exchange/` — Exchange integrations (ccxt)
- `src/strategy/` — Trading strategies
- `src/trading/` — Trading logic
- `src/ai/` — AI decision making
- `src/web/` — Web interface (FastAPI)
- `src/data/` — Data ingestion
- `src/backtesting/` — Backtesting engine
- SQLite persistence, Pydantic config, paper trading mode.

### Parseltongue (`/root/parseltongue/`)
- React/TypeScript browser extension
- Webpack build, Tailwind CSS
- Uses `js-tiktoken` for tokenization
- `src/` — Extension source

### GBrain (`/root/gbrain/`)
Postgres-native RAG knowledge brain. TypeScript/Bun.
- `src/core/` — Core engine, types, operations, embedding, link extraction
- `src/core/minions/` — Sub-agents for processing
- `skills/` — Skill definitions
- `tools/` — Tool implementations
- `tests/` — Test suite
- `evals/` — Evaluation harness

### Atomic (`/root/atomic/`)
Rust/Tauri personal knowledge base. Cargo workspace:
- `atomic-core` — Core library
- `atomic-server` — Server binary
- `atomic-cloud` — Cloud sync
- `mcp-bridge` — MCP protocol bridge
- `atomic-bench` — Benchmarks
- `src-tauri/` — Tauri desktop app

### Hermes WebUI (`/root/hermes-webui/`)
```bash
cd /root/hermes-webui
bash ctl.sh                # Control script (start/stop/restart)
```

## General Notes

- Python projects use `uv` for package management (not pip), except ai_stock_trader which uses pip/venv.
- Hermes Agent is the primary AI agent framework — gbrain and atomic integrate with it as memory/knowledge backends.
- Each project is self-contained with its own dependencies and config.
- Trading bots use `.env` files for API keys and configuration.
- Browser extensions (Parseltongue) use Webpack for bundling.
- Several projects have their own CLAUDE.md with deeper project-specific guidance (OmniRoute, atomic, gbrain).
