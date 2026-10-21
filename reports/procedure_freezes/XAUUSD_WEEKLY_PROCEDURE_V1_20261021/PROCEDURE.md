# XAUUSD Weekly Forecast Procedure V1

Status: FROZEN PROCEDURE REFERENCE. Freeze date: 21 October 2026, Africa/Nairobi (UTC+3).
Procedure ID: XAUUSD_WEEKLY_PROCEDURE_V1_20261021.
Scope: the accepted weekly evidence-to-Codex-forecast workflow, its forecast-file lifecycle, and its DAILY/EVALUATE interfaces. This freeze documents the existing rules and observed data-integrity checks. It does not create a trading signal, update price levels, change the extractor, or freeze an entire application or research model.

## 1. Authority and responsibility

AGENTS.md is the controlling repository instruction. Use prompts/weekly.md for WEEKLY, prompts/daily.md for DAILY, and prompts/evaluate.md for exact-cutoff reconstruction, entry timing, no-chase or a verdict. This reference must not weaken those instructions.

Required sequence: MT5 memory CSVs -> Python factual extractor -> validated evidence package -> Codex analysis -> final report and applicable Codex verdict. Codex must complete the analysis; package generation alone is not completion. Do not recommend another-AI handoff.

Python may extract, derive close_time, filter, validate, compute indicator values and numerical metrics, and reconstruct mechanical events. Python must not independently decide direction, permission, structural confirmation, entry confirmation, invalidation, no-chase block or the final trading verdict. A script that serializes explicitly Codex-authored conclusions is not an independent trading engine.

## 2. Establish the forecast week and causal cutoff

Record the exact forecast week, source broker symbol, requested cutoff, source clock convention and reporting timezone. The current instrument is XAUUSD.pro. The repository refresh module is selected with --symbol XAUUSD and must report MT5_SYMBOL=XAUUSD.pro; package metadata can use --symbol XAUUSD.pro.

A normal coming-week forecast uses only completed evidence before that week begins. Select and record the actual final relevant completed trading boundary. Do not substitute a weekend wall-clock cutoff that creates an artificial stale-data finding during a market closure. Do not assume every symbol shares the same session calendar.

CSV time is candle OPEN time. Derive close_time from timeframe duration: H4 240 minutes, H1 60, M30 30, M15 15. Export only close_time <= requested_cutoff. Never use a forming candle. A source filename or current machine date does not establish candle finality.

A midweek reconstruction must also derive its weekly map from preweek evidence. Record evidence_cutoff separately from actual created_at/frozen_at/valid_from. Never falsify the issuance time or backdate forecast validity. Disclose that reconstruction after seeing current-week action is not a blind, out-of-sample forecast even if numerical inputs are causally filtered.

## 3. Refresh and generate evidence

Use the existing local environment and accepted source code. From C:\Ben\mt5:

    .\.venv\Scripts\python.exe institutional_data_extraction.py --symbol XAUUSD

Confirm the exact resolved broker symbol, extraction clock, source tails and connectivity. Do not use --run-analysis to replace Codex's final discretionary analysis.

Then build the package with the chosen preweek cutoff; substitute the actual cutoff and a suitable output destination:

    .\.venv\Scripts\python.exe xauusd_prompt_extract.py weekly --h4 live_memory/xauusd_h4_memory.csv --h1 live_memory/xauusd_h1_memory.csv --m30 live_memory/xauusd_m30_memory.csv --m15 live_memory/xauusd_m15_memory.csv --symbol XAUUSD.pro --cutoff "YYYY-MM-DD HH:MM:SS" --output output --zip

Default windows are H4 90, H1 96, M30 120, M15 160. Record explicit overrides. Use the accepted exporter and preserve its output fields. Weekly/daily CLI packaging does not attach or validate the frozen weekly map automatically; the analysis layer must perform that validation explicitly.

## 4. Validate completeness and source finality

Read the manifest and exported CSVs. Check symbol, schema/version, chronology, duplicates, OHLC integrity, indicator availability and every exported close_time. Check close_time equals open plus duration. Separate raw-source latest metadata from causal exported latest metadata. common_effective_cutoff must derive from extracted causal endpoints and must not exceed requested_cutoff.

Compare actual tails with EXPECTED LATEST COMPLETED boundaries, accounting for the verified source clock and relevant trading sessions. An ordinary age gap inside an unfinished candle is not staleness. Examples: cutoff 03:45 expects H4 00:00, H1 03:00, M30 03:30, M15 03:45; cutoff 23:30 expects H4 20:00, H1 23:00, M30 23:30, M15 23:30 for the currently verified broker schedule.

The snapshotted extractor has a known age-based warning behavior: a timeframe can be flagged stale simply because its last completed close precedes the cutoff. Preserve that original manifest; save an independent expected-boundary validation and explain the discrepancy. A source-code hash is code identity, not certification that every manifest flag is correct. Do not quietly relabel missing candles as complete.

When recent official MT5 bars revise after nominal completion, lag ticks, or lack clear finality, verify their completed bid OHLC against historical ticks for exactly [bar_time, close_time). Verify coverage through the interval end and exclude all endpoint/future ticks. Preserve broker-wall-clock mapping supported by repository evidence; do not apply an unverified timezone conversion. Save tick counts, first/last times, OHLC, observation time, original official values and comparison results. Retain raw recent ticks or a reproducible retrieval/audit when practical. Repeat the fixed-interval check if stability remains uncertain.

Use the existing accepted tick-fallback/merge/enrichment functions for separate supplemental completed-input copies when needed. Recompute indicators from the causal warm-up history, not from future rows. Keep original data and manifests, mark superseded versions, and record provenance. Full H4/H1/M30/M15 boundary validation still applies to supplemental evidence. These checks do not authorize changing the frozen extraction logic.

If materially necessary M15/M30 evidence cannot be validated, return INCOMPLETE EVIDENCE with exact missing/stale intervals. Do not infer an unobserved path. Genuine missing H4/H1 context must likewise be identified rather than fabricated.

## 5. Perform the complete Codex weekly analysis

Classify H4 as trend, correction, transition or range, with invalidation context. Assess H1 continuation, cooling, transition or rejection state. Analyze M30/M15 context where relevant without confusing lower-timeframe activity with full entry permission.

Use preweek price history first: repeated swing highs/lows, completed reactions, range position, EMA/pivot context, ATR, MACD, wick and candle-body evidence. Distinguish an observation from an interpretation. A negative MACD main, histogram sign and histogram slope are separate facts; do not describe improving negative histogram as bearish acceleration. No calibrated probability or exact future range may be claimed without supporting validation.

Map support, control, resistance, target and target-turn zones. For each zone record its id, role, bounds, priority, direction context and historical basis. Define a primary expected sequence and alternate sequence, their required confirmations and explicit failure/invalidation conditions. A failed primary path may activate a predeclared alternate without redrawing the levels. Dynamic EMA values and new daily reaction references are context, not silent replacements for frozen zones.

## 6. Freeze levels and provenance

Create a new unique forecast_id and versioned directory. Do not overwrite an already frozen version. Write valid weekly_levels.json with schema_version, forecast_id, symbol, forecast_type, actual frozen_at, valid_from, valid_to and levels. Record evidence_cutoff, source/report timezone, primary/alternate paths, explicit invalidations and provenance. Each level has unique id, supported role, ordered low/high and priority. Validate through the existing level loader.

Record actual issuance time accurately. frozen_at <= valid_from must hold. Forecast validity cannot begin before actual issuance for live decisions. For the existing XAUUSD_WEEK_20261019_V1, the map also explicitly requires fully post-freeze M15 candles for new qualification/trigger; bars spanning that actual freeze remain context. Preserve that version-specific condition rather than silently rewriting it into a historical signal.

Save the complete weekly report and evidence manifest. Save a SHA-256 freeze receipt covering the versioned map and evidence used. Preserve the previous active forecast before updating output/levels/weekly_levels.json to the new version. Verify active and versioned copies match. Do not automatically reuse a forecast after valid_to.

A freeze receipt is a reproducibility and change-detection record, not a claim that files cannot be edited or a guarantee of profitable forecasts. New versions must be distinguishable; old versions and audit history remain reviewable.

## 7. Required final weekly report

Return the complete format in prompts/weekly.md: evidence completeness and expected/actual endpoints; source/report timezone and cutoff; FINAL/PROVISIONAL/INCOMPLETE EVIDENCE status; H4 regime; H1 setup; frozen weekly map; primary/alternate paths and invalidations; created levels file; confidence, limitations and data warnings. Link the resulting report and frozen map. A ZIP/manifest-only response is insufficient.

If reconstructed midweek, present the original preweek scenario separately from its current status, and preserve the actual creation timestamp. Do not claim historical trades were permitted under a forecast that did not yet exist.

## 8. DAILY and EVALUATE interface

DAILY validates current completed evidence against the same forecast version, reports nearest active frozen levels and completed interactions, and returns a context/watch report. DAILY does not quietly redraw levels or issue a fresh-entry verdict in place of EVALUATE.

EVALUATE uses an exact cutoff and validates every timeframe against its expected boundary. Reconstruct first touch, M15 qualification, M15 trigger, M30 confirmation, H1 permission and first simultaneous full confirmation using actionable close_time. Preserve bar_time too. The hierarchy remains H4 regime -> H1 directional permission -> M30 structural confirmation -> M15 qualification/trigger evidence.

Use the frozen forecast's stated setup criteria. The controlling AGENTS.md definition requires M15 qualified or triggered, M30 confirmation, H1 permission, valid forecast and compatible H4; do not silently replace it with a universal extra gate. Where a particular frozen setup explicitly requires a subsequent trigger, preserve that setup-specific condition. Current V1 uses such a subsequent-trigger sequence. A qualification candle cannot be its own subsequent trigger. A touch is not an entry. EMA state alone need not establish a local structural break. Explain evidence and missing gates explicitly.

Never backdate full confirmation to an earlier M15 event if a required later M30/H1 gate arrives afterward. Existing completed H1 evidence may provide current directional context; do not invent an H1 candle at a non-hour cutoff or impose a new H1 completion merely because a lower-timeframe event happened later. Full confirmation is the earliest causal time when the required gates coexist under a valid issued forecast.

## 9. No-chase and final verdict

Fresh entry requires BOTH consumption strictly <65% AND remaining room >=2.5 M15 ATR. Use ATR and price at exact first full confirmation, and distinguish a fresh entry at the requested cutoff from management of an existing position.

BUY: leg = opposing level - turn reference; consumed = confirmation price - turn reference; remaining = opposing level - confirmation price.
SELL: leg = turn reference - opposing level; consumed = turn reference - confirmation price; remaining = confirmation price - opposing level.
Consumption percent = consumed / leg * 100; remaining ATR = remaining / M15 ATR at confirmation.

Use the valid turn reference and nearest unconsumed opposing frozen boundary; do not skip an intervening zone to manufacture room. Before full confirmation, a numerical location screen is PROVISIONAL. It cannot establish confirmation-time PASS, BUY ALLOWED or SELL ALLOWED. Do not invent a turn reference, confirmation price or confirmation-time ATR to fill a table. A provisional no-chase pass does not override missing gates.

EVALUATE final verdicts are only: WATCH; EARLY TURN; M15 QUALIFIED; M15 TRIGGERED; WAIT; ENTRY CONFIRMED; BUY ALLOWED; SELL ALLOWED; TECHNICALLY CONFIRMED — NO-CHASE BLOCK; INVALIDATED; MANAGE EXISTING POSITION; INCOMPLETE EVIDENCE. Use INCOMPLETE EVIDENCE for material evidence deficits, not as a substitute for deciding a fully evidenced setup with unmet gates. A technically unconfirmed setup is not TECHNICALLY CONFIRMED — NO-CHASE BLOCK. Position management is a separate assessment; no trade execution is authorized by this procedure.

## 10. Preservation and change control

The accepted extractor logic remains frozen. Do not modify causal filtering, close-time handling, completeness calculations, event reconstruction, phase handling or accepted output fields without a reproducible extraction/data-integrity defect and regression coverage. No discretionary Python BUY/SELL engine may be introduced. This procedure freeze does not repair known warning behavior.

The authoritative source snapshots and hashes in this directory capture the baseline. Run verify_freeze.py before relying on baseline identity. It reports snapshot corruption separately from live source drift; it does not overwrite or roll back files. Legitimate later versions do not silently replace this V1 record. Keep data snapshots, procedure versions and price-forecast versions separate.

The following accepted methodology checks remain mandatory after extractor, prompt or rule changes; their analytical outcomes are Codex decisions, not Python verdict logic:

- 10 Aug 2026 07:00: M15 triggered; M30/H1 incomplete; final WAIT.
- 10 Aug 2026 08:00: first full BUY confirmation 08:00; no-chase passes.
- 11 Aug 2026 14:45: first full confirmation 14:00; BUY remains valid.
- 13 Aug 2026 06:30: first technical SELL confirmation 06:00; no-chase blocks.
- 14 Aug 2026 12:00: qualification 06:30, trigger 06:45, full confirmation 11:00.
- 03:45 boundary: H4 00:00, H1 03:00, M30 03:30, M15 03:45 are current.
- Stale source: H4/H1 12:00, M30/M15 07:30 -> incomplete with stale M30/M15.
- Future rows: remove all rows after requested cutoff; they never influence indicators or verdict.

Preserving this case list or passing extractor unit tests is not a claim that every historical Codex analytical report was re-executed. Record exactly which checks were run and their results.

## 11. Verification command

From C:\Ben\mt5:

    .\.venv\Scripts\python.exe procedure_freezes/XAUUSD_WEEKLY_PROCEDURE_V1_20261021/verify_freeze.py

Expect intact frozen snapshots and no live source drift immediately after this freeze. Active price levels and incoming CSV data are not hash-pinned as live sources by this procedure; they have their own forecast/evidence receipts. The archived 19 October forecast is contextual provenance, not a permanent price map for all future weeks.
