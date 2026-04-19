# Plan: Issue #42 — Create `tradingview-screener` Agent Skill

## Branch
`feature/issue-42-tradingview-screener-skill`

---

## 1. Overview

This issue delivers a new agent skill located at
`.github/skills/tradingview-screener/` that teaches downstream agents how to
construct accurate queries using the `tradingview-screener` Python library
(pinned at `2.5.0` in the codebase). The skill covers the full query API
(`Query()`, `.set_markets()`, `.set_index()`, `.select()`, `.where()`,
`.limit()`, `.get_scanner_data()`), the canonical set of supported column
names, and known pitfalls (ticker prefix format, `is_primary` filtering,
`NaN` behaviour for non-equity instruments). Success is defined as: an agent
consuming this skill can construct a working `tradingview-screener` query
with correct field names and receive a valid `pd.DataFrame` on the first
attempt, with no manual field-name corrections required.

---

## 2. Constraints & Conventions

All downstream agents executing these stories MUST respect the following rules.

| # | Rule |
|---|------|
| C1 | Skill directory must be exactly `.github/skills/tradingview-screener/` (lowercase, hyphen). |
| C2 | `SKILL.md` must carry valid YAML frontmatter with `name: tradingview-screener` and a `description` of ≤ 1 024 characters. |
| C3 | `SKILL.md` body must not exceed 500 lines / 5 000 tokens. |
| C4 | All large reference content (field catalogue, gotchas, examples) goes in `references/` sub-directory and is loaded on demand — it must NOT be inlined in `SKILL.md`. |
| C5 | No existing file in the repository may be modified as part of this issue. |
| C6 | Every deviation from this plan must be logged in `.github/issues/42/development_notes.md`. |
| C7 | Commit messages must follow the pattern `<prefix>(issue-42): <imperative description>` where prefix is one of `feat`, `config`, `build`, `fix`. |
| C8 | The skill must not introduce or reference any network-dependent code. It is documentation only. |

### Repo context

- `.github/skills/` already exists and contains five skills:
  `design-systems-specialist`, `github-project-manager`,
  `implementation-specialist`, `qa-auditor`, `tech-stack-architect`.
- Each existing skill directory contains only a single `SKILL.md` file with
  YAML frontmatter (`name`, `description`) followed by a markdown body.
- `.github/issues/` already exists with one precedent (`issues/41/`). Issue
  41 established the `plan.md` / `development_notes.md` / `implementation.md`
  document pattern which this issue follows.
- `tradingview-screener==2.5.0` is already a pinned dependency in
  `tayfin-ingestor/tayfin-ingestor-jobs/requirements.txt` (added in Issue 41).
- A knowledge guide for the library already exists at
  `docs/tradingview_screener/TRADINGVIEW_SCREENER_GUIDE.md` — the new skill
  references and extends this material.

---

## 3. Delivery Stories

| # | Story | Description | Commit prefix | Commit message |
|---|-------|-------------|---------------|----------------|
| 1 | Scaffold skill directory | Create `.github/skills/tradingview-screener/SKILL.md` with valid YAML frontmatter only (`name`, `description`) and a placeholder body. Confirm `name` is `tradingview-screener`, `description` is ≤ 1 024 chars and keyword-rich. | `feat` | `feat(issue-42): scaffold tradingview-screener skill directory and SKILL.md stub` |
| 2 | Write core `SKILL.md` body | Replace the placeholder body with full activation instructions: when to load the skill, how to construct a `Query()`, method chain reference (`.set_markets()`, `.set_index()`, `.select()`, `.where()`, `.limit()`, `.get_scanner_data()`), shape of the returned `(count, DataFrame)` tuple, ticker prefix convention (`BIST:THYAO`), and one end-to-end BIST XU100 example. Add `references/` load-on-demand instructions for field catalogue, gotchas, and examples. | `feat` | `feat(issue-42): write core SKILL.md instructions and query API reference` |
| 3 | Add field reference catalogue | Create `references/fields.md` with the canonical grouped list of supported column names drawn from the official docs (https://shner-elmo.github.io/TradingView-Screener/fields/stocks.htm). Groups: **Price / OHLCV**, **Fundamentals**, **Market info**, **Index membership**. Each entry: column name (string literal), data type, short description. Add one-line instruction at the top of the file explaining its purpose and how to cite it. Update `SKILL.md` to include the on-demand load instruction for this file. | `feat` | `feat(issue-42): add field reference catalogue to references/fields.md` |
| 4 | Add gotchas & edge-case reference | Create `references/gotchas.md` documenting: (1) ticker format is always `EXCHANGE:SYMBOL` — never bare `SYMBOL`; (2) `is_primary == True` filter required to suppress duplicate cross-listings; (3) `market_cap_basic` is `NaN` for ETFs and participation certificates; (4) `raw_count` (total server-side match count) always exceeds `len(df)` when `.limit()` is applied; (5) no authentication or session cookies required for screener queries; (6) `.get_scanner_data()` performs a live HTTP call — outputs are non-deterministic across runs. Update `SKILL.md` to include the on-demand load instruction for this file. | `feat` | `feat(issue-42): add gotchas and edge-case reference to references/gotchas.md` |
| 5 | Add usage examples | Create `references/examples.md` with 4 annotated Python examples: (a) BIST XU100 index constituents (the current production query from `tradingview_bist.py`), (b) top-20 BIST stocks by market cap, (c) BIST stocks filtered by a fundamental threshold (e.g. P/E < 10), (d) multi-market query (USA + Turkey). Each example includes: the Python code block, expected column set in the resulting `DataFrame`, and a JSON-format sample row. Update `SKILL.md` to include the on-demand load instruction for this file. | `feat` | `feat(issue-42): add annotated usage examples to references/examples.md` |
| 6 | Final review & self-validation | Re-read all skill files against the spec checklist: frontmatter validity, line count ≤ 500, all relative paths in `SKILL.md` point to existing files one level deep under `references/`, no broken links, branch is `feature/issue-42-tradingview-screener-skill`. Write `.github/issues/42/development_notes.md` with any deviations, open items, and a completion summary. | `feat` | `feat(issue-42): self-validation pass and development_notes.md` |

---

## 4. Open Questions

The following items are ambiguous or require a decision before or during
implementation.

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| Q1 | Should the skill include a `scripts/` directory with a smoke-test helper that runs a live query? If so, it would require network access in the agent's execution environment. | Expands scope — may violate C8 (skill is documentation only). | `@lead-dev` to decide before Story 1 ships. |
| Q2 | Is network access to TradingView guaranteed in the agent's execution environment? The `gotchas.md` will note that `.get_scanner_data()` is a live HTTP call, but should the skill also document an offline / mock fallback pattern? | Affects Story 4 content and Story 5 examples. | `@lead-dev` to clarify before Story 4. |
| Q3 | Should the `SKILL.md` frontmatter include a `compatibility` field specifying the minimum `tradingview-screener` version (`>=2.5.0`)? The Agent Skills spec does not mandate this field, but it may prevent confusion when the library is upgraded. | Low — cosmetic, no functional impact. | Implementer can decide at Story 1 unless `@lead-dev` objects. |
| Q4 | The existing `docs/tradingview_screener/TRADINGVIEW_SCREENER_GUIDE.md` covers `get_all_symbols()` only and predates the `Query()` API usage in `tradingview_bist.py`. Should this guide be expanded, or should the skill be the canonical reference? If the guide is to be updated, it falls outside this issue (C5: no existing files modified). | Determines whether the skill should cross-reference or supersede the guide. | `@lead-dev` to clarify. Note that updating the guide is explicitly out of scope for Issue 42. |
| Q5 | Should `references/fields.md` be generated programmatically (by scraping https://shner-elmo.github.io/TradingView-Screener/fields/stocks.htm) or written manually from the documented field list? Programmatic generation would be more complete but requires network access in the agent session. | Affects Story 3 approach. | `@lead-dev` to decide. Default assumption: manual, curated list. |

---

## 5. Out of Scope

The following items are explicitly excluded from Issue #42:

- Modifying any existing job, config, provider, or skill file.
- Creating a new scheduled job, data pipeline, or database migration.
- Changes to `tayfin-ingestor`, `tayfin-indicator`, `tayfin-screener`, or
  `tayfin-app` bounded contexts.
- Expanding `docs/tradingview_screener/TRADINGVIEW_SCREENER_GUIDE.md`
  (existing file — modification is prohibited by C5).
- UI or API surface changes.
- Adding `tradingview-screener` to any other `requirements.txt` beyond the
  one already updated in Issue #41 (already done — out of scope here).
- Writing unit or integration tests for the skill content (the skill itself
  is documentation, not executable code).
