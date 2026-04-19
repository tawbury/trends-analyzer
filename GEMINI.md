# Gemini CLI Configuration: Trends Analyzer

> [!CAUTION]
> ## Mandatory Agent Context Sync
> **This rule is executed automatically in every session and every task. No exceptions.**
> You MUST update the **Current Goal** section in `AGENTS.md` before starting work based on the branch and task. Also, record new components, functions, or patterns in the **Code Consistency Rules** section of `AGENTS.md` to maintain project-wide consistency.
>
> ### Auto-Execution Checklist
> | Timing | Action | Required |
> |------|----------|------|
> | **Before Work** | Check branch via `git branch --show-current` -> Update **Current Goal** in `AGENTS.md` | **Mandatory** |
> | **During Coding** | Create new component/function/pattern -> Record in **Code Consistency Rules** in `AGENTS.md` | **Mandatory** |
> | **On Completion** | Check completion conditions and reflect results in `AGENTS.md` | **Mandatory** |
> | **On `/pdca analyze`** | Always run `ruff check --fix .` before Gap Analysis to ensure a clean linter state for accurate Match Rate. | **Mandatory** |
> | **Legacy Files** | Create a `backups/` folder, move legacy files there, then delete originals. | **Mandatory** |
> | **PDCA Docs** | Add all PDCA documents to `.gitignore` to exclude from git tracking, except for the `archive` folders. | **Mandatory** |

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
- **Linter Enforcement**: Ensure no linter errors exist before performing `/pdca analyze`.

## Documentation Rules
- **Language**: All documentation and comments MUST be written in Korean (한글). Code identifiers (variables, classes, functions) remain in English.

## Safety & Security
- Never commit `.env` or secrets.
- Check `is_korean_market_hours` before executing heavy tasks.
- Maintain idempotency for all write/heavy endpoints.
- Protect `.git`, `AGENTS.md`, and `GEMINI.md` from unauthorized modifications.
