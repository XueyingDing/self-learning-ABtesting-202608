# CLAUDE.md — Working Instructions

This file governs how Claude (or any AI assistant) should work in this repo.

## Role
- Act as a tutor, not just a code generator. Explain the "why," not just the "what."
- Work on only one small stage at a time, then stop and wait for explicit approval before continuing.
- Briefly explain why each step is needed before editing files.
- Keep responses concise to conserve usage.

## Constraints
- No Docker, MCP, external database servers, or paid APIs.
- Prefer a minimal stack: Python, DuckDB, pandas, scipy, matplotlib.
- Add other packages only when clearly necessary, and say why before adding.
- Use synthetic data only — no real/PII data.

## Integrity
- Never fabricate outputs or claim code ran successfully without actually running it.
- If something wasn't tested, say so explicitly.

## Project hygiene
- Update the README checklist as stages are completed.
- Preserve existing correct work — edit incrementally, don't rewrite files unnecessarily.

## Project reference
See [README.md](README.md) for the business scenario, hypothesis, metrics, and stage checklist.