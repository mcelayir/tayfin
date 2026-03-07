# Research Specs

This directory stores reference material for financial indicator mathematics and algorithm specifications.

## Purpose

- **Indicator math specs:** Formal definitions of SMA, EMA, ATR, VCP, and other indicators used by Tayfin.
- **Algorithm pseudocode:** Step-by-step logic that the Developer agent implements and the QA agent validates against.
- **Reference papers/sources:** Links or summaries of authoritative sources for each algorithm.

## Usage

- The **QA agent** uses these specs during the "Financial Math Check" step of validation.
- The **Developer agent** references these specs when implementing indicator logic.
- The **Lead Dev** creates new spec files here when an ADR introduces a new indicator or algorithm.

## Naming Convention

```
{indicator_name}_spec.md    (e.g., vcp_spec.md, sma_spec.md)
```
