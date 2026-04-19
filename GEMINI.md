# Gemini CLI Configuration: Trends Analyzer

## Core Mandates
- **PDCA Workflow**: Follow Plan -> Design -> Do -> Check -> Act -> Report.
- **Contextual Precedence**: This `GEMINI.md` and `AGENTS.md` are the source of truth for project rules.
- **Source of Record Priority**:
    1. Current project code and file structure.
    2. `AGENTS.md`.
    3. `docs/meta/docs_index.md`.
    4. `docs/architecture/` and `docs/specification/`.

## Architecture Principles
- **Trend Core as SSOT**: Maintain `src/core/` as the single source of truth for normalization, deduplication, filtering, scoring, and aggregation.
- **Consumer Ignorance**: Core logic must not know about consumers (QTS, n8n, etc.). Use Adapters in `src/adapters/`.
- **API-First**: Maintain a formal API layer at `/api/v1`.
- **Market Hours Guard**: Strictly forbid heavy jobs (batch, mass ingestion, LLM analysis) during KST 09:00~15:30.

## Code Consistency Rules
- **Use Cases**: Orchestrate logic in `src/application/use_cases/`.
- **Contracts**: Fix dependencies using data contracts in `src/contracts/`.
- **Adapters**: Split QTS, Generic, and Workflow adapters in `src/adapters/`.
- **Persistence**: Prefer PostgreSQL. Use JSONL only for initial validation or auxiliary storage.
- **Scoring**: Implement multi-dimensional scores (relevance, sentiment, impact, confidence, novelty, urgency, actionability, content_value).
- **Credibility**: Use `src/core/credibility.py` for source-tier-based evaluation.

## Operational Rules
- **Market Protection**: Prioritize QTS/Observer stability. Use CPU/memory limits and time separation.
- **Batch Windows**: Prefer 06:00~08:00, 16:00~18:00, and 20:00~23:00 KST.
- **Local-First**: Validate in WSL2 before OCI deployment.

## Safety & Security
- Never commit `.env` or secrets.
- Check `is_korean_market_hours` before executing heavy tasks.
- Maintain idempotency for all write/heavy endpoints.
