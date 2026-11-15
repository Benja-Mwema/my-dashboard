# WS30 dashboard feature update — 15 November 2026

The WS30 dashboard now provides AUDCAD-style inspection and export features while retaining the four frozen WS30 rules and archived results.

## Features

- Instrument navigation, current snapshot/frozen deployment replay, manual reload and visible-page refresh every 15 minutes.
- Combined BUY/SELL or direction-specific views; cohort, model, outcome and month filters.
- Filtered admission counts, nonnegative rate (including BE), target-hit rate and gross R with shared-economic-entry disclosure.
- Entry selector and latest-entry shortcut; selection survives refresh and clears when excluded by filters.
- Journey chart with dotted target guide, solid observed prices, adverse dotted segments, actual BE activation, archived exit and purple post-TP context. 48 H1 bars or latest available observation.
- Technical chart with candles, display-only EMA10/20/50/200 and MACD12/26/SMA9. Original ATR chart and M15/M1 evidence preserved.
- Confirmation-time indicator table using completed native H1 candles only.
- Ledger includes TP/SL, exit time, gross index units, sampled favourable close movement, overlaps and detection/origin. CSV exports respect filters; raw snapshot download and replay acceptance available.
- Existing prospective paper journal and source governance remain separate from historical results.
- Errors clear stale evidence and disable exports; wrong symbol, scale and rule hashes fail closed. Mobile table scrolling stays within page width.

## Instrument-specific boundaries

WS30 keeps TP +2ATR, SL -3ATR, +1ATR BE threshold with the existing H1 two-candle rule and 24-H1 horizon. AUDCAD's 60-pip levels and M30 retracement exit were not transplanted. The >50% H1 completed-close retracement marker is chart annotation only. One R remains initial 3ATR risk; native broker point is 0.1. All 189 historical admissions and frozen scores are unchanged.

Sampled favourable close movement uses completed H1 closes before exit plus the archived nominal exit reference. It is not intrabar MFE. Display indicators seed at the first published native H1 close and are not the frozen strategy's calculation authority. M1 evidence contains archived entry/exit windows; M15 post-TP context is limited to archived coverage. No post-exit context contributes to P/L.

## Verification and deployment

`tools/test_ws30_features.py` runs real Chromium desktop/mobile checks, filtered CSV download, 189-row score equality, chart modes, BE/TP behaviour, replay selection, reload recovery and wrong-instrument rejection. Local acceptance is recorded in `tools/ws30_features_acceptance.json`. Run with `--url https://my-dashboard-olo8.onrender.com` for public verification.

Runtime entry and scoring engines, active publisher, live JSON snapshots and other instrument assets are unchanged. Static presentation assets are released from an isolated Git worktree; the existing shared publisher can fast-forward normally.

Rollback: revert the feature release commit; retain existing snapshots and paper journals. The added `ws30-replay.json` is the original deployment replay, not a recomputed performance sample.
