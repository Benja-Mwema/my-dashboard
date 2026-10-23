# Implementation status — XAUUSD V1.1 / V2.1

**Decision: STAGED — REVIEW REQUIRED. No live promotion.**
**Prepared:** 23 October 2026, Africa/Nairobi (EAT, UTC+3).
**Research root:** `C:\Ben\mt5\research_candidates\XAUUSD_V1_V2_UPGRADE_20261023\`.

## What is ready

Two isolated candidate procedures and Codex overlays are written. V1.1 preserves V1's substantive forecast and EVALUATE rules while adding a separate package checker, explicit source/cutoff/boundary reporting, local immutable record registration, and hash receipts. V2.1 requires separate conclusions for completed-H4 authority, first conditional leg, weekly-close preference, and EVALUATE-only fresh entry; it adds protected-swing timing, strongest countercase, opening-premise checks, route event order/lifecycle, and explicit abstention/coverage reporting.

The adapters do not make trading decisions. The V1.1 validator checks exported candle schemas, indicator presence, finite numeric values, sorted unique opens, OHLC consistency, timeframe close arithmetic, causal cutoff, window length, and file hashes. It requires expected session close inputs rather than inferring a broker calendar. `FINAL` requires an independent source-session/clock and tick-finality certificate with matching boundaries. The adapter also reconstructs factual route-event ordering and calculates no-chase numeric fields only after a separately Codex-authored full-confirmation flag; it never emits an official PASS/BLOCK or trade verdict. The research registry writes uniquely named records and receipts without replacing an existing forecast ID. Receipt hashes are local integrity checks, not trusted external timestamps.

The source-backed examples use the archived 17 October preweek evidence for the 19–23 October week. Both are explicitly labeled historical reconstructions because the existing V1 map was actually issued 20 October at 23:14:14 EAT. The V1.1 example retains the existing V1 analysis as reporting provenance demonstration; the V2.1 example shows the separate four-field reasoning contract. Neither example is a prospective forecast or official EVALUATE record.

## Baseline facts and evidence limits

- `C:\Ben\mt5` has no Git repository, so no branch or status is available. The new work is staged in a unique research directory created under the authorized workspace.
- Source instrument is `XAUUSD.pro`; the accepted refresh selector is `--symbol XAUUSD`. No refresh was run. Original `live_memory` was read-only for this task.
- The local environment is `.venv` with Python 3.14.4 and pytest 9.1.1.
- Live memory file tails: H4 opened 22 Oct 04:00; H1 22 Oct 07:00; M30 22 Oct 08:00; M15 22 Oct 08:15 (source clock). These tails are not final preweek evidence for a new 26 October forecast and were not refreshed or session-certified.
- Archived package `output/weekly_20261016/` is for cutoff 17 Oct 00:00 EAT. The original independent validation records H4/H1/M30/M15 expected and actual close 17 Oct 00:00, with 90/96/120/160 rows, valid causal filtering, correct durations, no duplicate timestamps, and no within-session gaps. The new independent validator agrees on the supplied boundaries and row facts but reports **PROVISIONAL** because it does not independently certify the session clock or tick finality.
- Active map `output/levels/weekly_levels.json` is `XAUUSD_WEEK_20261019_V1`, frozen 20 Oct 23:14:14 EAT. Its identity is captured and unchanged. It is a late midweek reconstruction, not evidence of preweek issuance.
- The original V1/V2 prospective protocol covers 20 weeks from 26 Oct 2026 through 12 Mar 2027. It is planned, with zero forecasts and zero outcomes. Its journals were not modified. V1.1/V2.1 have no registered or prospective forecasts; the separate parallel-study protocol is only a draft.
- The V1, V2, and V3 freeze verifiers each pass snapshot/receipt integrity and source identity. These checks establish identity, not forecast performance.
- The original five August analytical cases remain compatibility contracts. The V2 validation record says they were not historically re-executed; full original issued map plus exact-cutoff Codex verdict records were not available as a matching set here. They remain `NOT_RUN_MISSING_INPUT`.

## Verification

- Frozen V1 verifier: PASS; live source identity MATCH.
- Frozen V2 verifier: PASS; fixed source identity MATCH.
- Frozen V3 verifier: PASS; receipt and snapshot PASS; fixed source identity MATCH.
- Accepted extractor tests: 17 passed on a fresh isolated pytest base directory.
- New candidate tests: 16 passed, covering boundary-duration arithmetic, causal future/forming rejection, declared close-time arithmetic, duplicate timestamps, impossible OHLC, stale lower-frame and short-window incompleteness, missing verified boundaries, certificate-gated FINAL state, route chronology, no-chase strict limits/inputs, backdated/late custody rejection, and exclusive immutable registration/hash receipts.
- Six JSON schemas/templates parse as JSON. This is syntax validation; no semantic Draft 2020-12 validator run is claimed.
- Archived preweek evidence inspection: H4/H1/M30/M15 row facts pass under explicitly supplied expected boundaries; source finality remains provisional.
- Protected baseline identity comparison is performed by `04_TESTS/verify_baseline_unchanged.py`; its final run is recorded alongside the checksum manifest.
- Full matrix is in `06_RESULTS_AND_DECISION/ACCEPTANCE_STATUS.md`. Structural-analysis, route-order, full-gate synchronization, exact-time no-chase, and August human-judgment cases are documented but not re-executed. There are no hidden test passes for those cases.

## Exact changes and preservation

New files exist only under this research root. There were no edits to `AGENTS.md`, baseline prompts, frozen V1/V2/V3 folders, accepted extractor files, `institutional_data_extraction.py`, original live-memory CSVs, active `weekly_levels.json`, archived map files, the V1/V2/V3 study protocols or journals, EA/trading settings, or the Render/AURUM deployment.

V1.1's intended behavioral difference is process-state clarity: incomplete/uncertified evidence must be surfaced instead of being interpreted as fully verified. On complete identical facts, the V1 map, setup conditions, gates, no-chase thresholds, and verdict are unchanged. V2.1 changes the weekly research report structure and route-analysis requirements only. The official EVALUATE hierarchy and taxonomy remain frozen. These candidates do not enter the original 20-week V1/V2 cohort.

## Required review before acceptance

This is not yet a mature operational release. A broker-session calendar adapter, tick-finality validation, broader route chronology fixtures, source-backed August replays, paired V1/V1.1 parity runs, and independent analyst review remain. Do not use it to issue a forecast or entry decision until those checks and a separate candidate review are complete. The original procedures remain the rollback path: stop using this folder; no production rollback is needed.
