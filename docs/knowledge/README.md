# Knowledge Base

This directory stores practical knowledge about tools, libraries, and integration patterns used in the Tayfin suite.

## Purpose

- **Tool guides:** Usage patterns, gotchas, and performance notes for libraries like `stockdex`, `yfinance`, `httpx`, etc.
- **Integration notes:** How external APIs behave (rate limits, data quirks, caching strategies).
- **Spike findings:** Summaries from Developer spike experiments that reveal non-obvious behavior.

## Usage

- The **PM agent** consults this directory to ensure tasks use the approved tech stack.
- The **Lead Dev** and **tech-stack-architect** skill use this as the primary knowledge retrieval source.
- The **Developer agent** (via the `implementation-specialist` skill) adds new entries here when spikes reveal important findings.

## Naming Convention

```
{tool_or_topic}/README.md    (e.g., stockdex/README.md, yfinance/README.md)
```
