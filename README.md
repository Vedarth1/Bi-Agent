# BI Agent — ask your database in plain English

A from-scratch AI agent (no frameworks) that answers natural-language questions
about a PostgreSQL database: it inspects the schema via tools, writes SQL,
guards it, executes it read-only, and returns prose + a chart spec.

## Demo
(screenshot of the UI with a bar chart + trace panel)

## Architecture
Browser (web/) → FastAPI (routes) → Agent loop (llm_service)
                                     ├→ tools.py  → db.py (psycopg, agent_ro)
                                     ├→ memory.py (sliding-window conversation memory)
                                     └→ Ollama (llama3.1/qwen2.5, tool calling + structured output)

## Security model (three layers)
1. System prompt with security rules (soft — bypassable by injection)
2. SQL validator: SELECT/WITH only, single statement, keyword denylist (app layer, bypassable)
3. Least-privilege DB role `agent_ro` (SELECT grants only — the layer that cannot fail)
4. Output filter for system-prompt leakage (hides, does not prevent)
Red-team results: 5 attacks, before/after table below.

## Evals
`python3 evals/run_evals.py` — 9 cases: exact-row ground truth (setseed-frozen fixture),
row counts, refusal cases, prompt-leak check, memory follow-up. Exit code gates CI.
Current score: 9/9.

## Failure modes I hit (and fixed)
- `localhost` inside a container ≠ host; fixed via `host.docker.internal` / service DNS
- vega-embed collapses `width: container` (inline-block); fixed with explicit block sizing
- one-round tool calls can't handle multi-step questions → generalized to the agent loop
- uncorrelated LATERAL with `ORDER BY random()` evaluates once, not per row → corrupted seed
- model emits tool calls as plain text → output-repair path
- confident wrong answers (summed prices instead of revenue) → frozen ground truth + evals

## Known limitations
- In-memory conversation store: dies on restart, not shared across workers (Redis is the upgrade path)
- 8B local model: prompt-leak prevention is imperfect (filtered, not prevented)
- Denylist SQL validation is usability, not security — the DB role is the security