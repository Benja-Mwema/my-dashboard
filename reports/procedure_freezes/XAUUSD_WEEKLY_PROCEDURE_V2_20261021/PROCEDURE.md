# XAUUSD Weekly Analysis Procedure V2

Status: FROZEN RESEARCH CANDIDATE, prospective comparison only.
Procedure ID: XAUUSD_WEEKLY_PROCEDURE_V2_20261021.
Reference: XAUUSD_WEEKLY_PROCEDURE_V1_20261021. Created 21 October 2026, EAT.

## Authority and boundary

AGENTS.md remains controlling. V1 remains intact. V2 is an analysis overlay for new research forecasts; it does not change the accepted extractor, baseline prompts, current issued price map, EVALUATE verdict taxonomy, or historical forecast validity. For each new prospective week, Codex produces both an unchanged V1 control and this V2 candidate from identical validated preweek evidence. Neither method's new map replaces an active live map automatically.

Codex must select the regime, directional preference or lack of preference, structural turns, zones, paths, invalidations, permissions, confirmation and no-chase verdict. Python may load and validate candles, calculate indicators and numerical room, reconstruct mechanical interactions, serialize explicitly Codex-authored records and count numerical agreement. Python must never independently decide the trading states prohibited by AGENTS.md. A stored decision label is not an algorithmic decision.

## Evidence workflow retained exactly

Use institutional_data_extraction.py and the accepted xauusd_prompt_extract.py WEEKLY path; use prompts/weekly.md as the baseline report format and this directory's weekly_v2.md as the analytical overlay. Use the default H4/H1/M30/M15 windows 90/96/120/160. No new signal algorithm or altered indicator definition is introduced.

Record source symbol XAUUSD.pro, source clock, EAT reporting clock, true extraction time, requested preweek cutoff and expected/actual latest completed endpoints for all four frames. Derive close_time from open time. Only close_time <= cutoff may enter the forecast. Retain raw tail metadata separately. Recompute indicators on causal prefixes where historical evidence is used. Use verified broker sessions; weekend or shortened-session gaps are not automatically staleness. Preserve the manifest and independent validation. Use tick verification for recent ambiguous or revised completed bars as V1 requires. Material evidence deficits remain INCOMPLETE EVIDENCE.

## Improvement 1: distinguish a corrective rebound from a directional regime turn

Codex must state H4 trend/swing sequence, EMA10/20/50/200 context, MACD main, histogram and histogram change separately. Identify the latest relevant completed swing boundary before proposing a structural turn.

When the proposed direction opposes the established H4 structure, or a BUY remains below H4 EMA200 / SELL above it, include a turn-evidence table with the exact swing price and originating candle, completed H4 acceptance/break time if any, support/resistance hold or failed retest evidence, and completed H1 structural permission. Describe why the evidence changes the preceding structure rather than merely slows its momentum. EMA200 is context, not a universal one-line directional veto. A histogram improvement, moving-average recovery or zone touch by itself is insufficient to promote a corrective leg into the dominant weekly outlook.

Without an explicit evidenced H4 turn and supporting H1 structure, keep the corrective path conditional. Codex may record weekly directional preference UNRESOLVED. This is a research forecast field, not an additional EVALUATE verdict. Do not invent missing turn evidence or force a binary weekly forecast. Primary and alternate paths must still be explicit. This is a qualitative Codex assessment, not a Python gate.

## Improvement 2: freeze the sequence and define the opening review

Before the week starts, record origin, nearest first objective, extensions only after intervening acceptance, H4 failure condition, alternate activation and alternate failure. Declare whether the primary is a support-hold, rejection, continuation or corrective path. State that origin must precede objective for origin-to-target credit.

At the first reviewed completed cutoff after market opening, Codex compares opening location and completed evidence with the unchanged map. Record a gap beyond a failure threshold, opening beyond the first target, absent origin revisit or already-consumed leg. An opening gap alone is not a completed-H4 invalidation when the frozen rule requires an H4 close. Nevertheless no entry may be inferred from the stale preweek sequence: apply all current gates and no-chase, and explain the disrupted premise. Preserve the frozen map; opening review is a separate dated observation. Do not silently move the origin or target.

## Improvement 3: enforce scenario lifecycle and separate time horizons

Codex records an observation lifecycle: unactivated, origin observed, gates pending/confirmed as applicable, first objective observed, primary failed, alternate under review, or expired. These journal descriptions do not replace the allowed EVALUATE final verdicts.

A completed failure event ends that declared branch. A target later in the week does not rescue it. A new setup requires a separately identified, timestamped assessment and the required gates; it is not retroactive reinstatement of the failed forecast. An alternate can be assessed only under its predeclared activation and failure conditions, not by choosing whichever path later looks successful.

Freeze a first-leg hypothesis separately from the weekly closing-direction preference. After first objective contact, use DAILY/EVALUATE to reassess extension or reversal with the same frozen map. Do not assume the initial direction persists through Friday. A target followed by failure is recorded as both events. A target visited before origin gets no origin-to-target credit; if both occur inside one OHLC bar, order is unresolved without sufficient finer evidence.

## Improvement 4: retain strict entry evidence and no-chase

WEEKLY remains scenario context. EVALUATE remains the only workflow for fresh-entry verdicts. H4 regime, H1 permission, M30 structure and M15 qualification/trigger must be evidenced at completed close_time. Preserve setup-specific trigger requirements and the earliest simultaneous confirmation rule. Do not backdate full confirmation to an earlier M15 event. Prior issued V1 maps retain their original criteria and real issuance times.

Keep both numerical thresholds unchanged: consumed leg strictly <65%, remaining room >=2.5 M15 ATR at exact first full confirmation, plus current-cutoff location recheck. Use the nearest unconsumed opposing boundary. Do not widen the target, skip zones, widen invalidation or adjust thresholds to repair the twenty-week sample. Before full confirmation, room calculations are provisional and cannot authorize an entry. Existing-position management remains separate.

## Improvement 5: make absence of opportunity visible

Report UNRESOLVED weekly preference, incomplete evidence, unvisited origin, unconfirmed gates, no-chase blocks and expired forecasts explicitly. A correct directional move without the stated setup is not a tradable success. Neither abstentions nor missing forecasts may disappear from performance denominators. An unactivated scenario is distinct from a directional miss and from an entry loss.

## Frozen forecast and report requirements

For every method/week, preserve the full report, evidence and independent validation, actual created_at/frozen_at/valid_from, forecast horizon and levels file. Include the preweek swing/turn evidence table, weekly preference and first-leg direction separately, origin, target and extension, explicit failure and alternate activation, opening-review requirements, confidence with reasoning and limitations. Use the existing level loader. Write only versioned research directories; never overwrite output/levels/weekly_levels.json as part of this study.

No historical valid_from may be manufactured. Every prospective forecast must be registered before Monday 00:00 EAT for its target week. A late record may be retained as late/reconstructed but is excluded from prospective accuracy and counted in coverage. Journal registration time establishes when the workspace recorded it, not an externally notarized timestamp.

## Prospective validation protocol

The fixed study is 20 consecutive target weeks from 26 October 2026 through 8 March 2027 (last Friday 12 March). The known 1 June-16 October sample is development evidence only. Do not rerun it and label tuned results independent validation.

Use identical causal evidence, cutoff, extractor/default windows and reporting clocks for V1 and V2. Codex completes and freezes V1 first, then V2; both must be frozen before the target week. Store separate manifests and method hashes. No new rules during the fixed block. A necessary correction creates a new version and is reported as a protocol deviation, not silently substituted.

At week end validate actual completeness before grading. If the broker has shortened sessions, preserve the verified actual cutoff; calendar dates are planning fields, not assumed session evidence. Final comparison waits until the full target week has ended. Preserve daily and full-week actuals. Python can calculate arithmetic; Codex determines scenario and gate interpretations.

Report all 20 scheduled weeks, eligible paired forecasts, late/missing/incomplete records, directional preference coverage, and the identical resolved-week subset for paired directional comparison. On that subset compare body direction and dominant excursion. Also show each method's own resolved-week accuracy with its denominator and its all-scheduled-week hit count. UNRESOLVED is not forced into BUY/SELL and does not count as a directional hit. Maintain counts of first-target-before-failure, subsequent failure, failed-before-target, unactivated and unresolved chronology. Never call these counts trade win rate.

Report unconditional BUY, unconditional SELL and previous completed week's body-direction benchmarks, on the same eligible evidence and paired subset. These are descriptive benchmarks, not trading recommendations. The old twenty-week sample had 13 down bodies and 15 downside-dominant weeks; its 50% method agreement did not beat those SELL baselines.

Entry evaluation is a separate predeclared study: at each reviewed completed cutoff, Codex must save qualification/trigger, M30/H1 evidence, first full confirmation, exact-time ATR/price/turn reference/nearest opposing edge, both no-chase calculations and final verdict. Save every reviewed cutoff including WAIT and incomplete cases. Until this record exists, report entry/no-chase performance UNSCORED; do not claim improvements to profitability, fills or trade success.

After the fixed block, assess V2 against V1, coverage and benchmarks. Twenty weeks is a small sample and no numerical improvement guarantees a stable advantage. V2 remains a research candidate until a separate recorded decision. No live promotion, execution or recurring automation is authorized by this procedure.

## Compatibility and preservation

The accepted extractor, baseline prompts and V1 snapshots remain unchanged. The accepted August analytical cases remain V1 compatibility contracts; V2 does not retrospectively rewrite their issued maps. Preserve these expected cases:
- 10 Aug 2026 07:00: M15 triggered; M30/H1 incomplete -> WAIT.
- 10 Aug 2026 08:00: first full BUY confirmation 08:00; no-chase passes.
- 11 Aug 2026 14:45: first full confirmation 14:00; BUY remains valid.
- 13 Aug 2026 06:30: first technical SELL confirmation 06:00; no-chase blocks.
- 14 Aug 2026 12:00: qualified 06:30, triggered 06:45, full confirmation 11:00.
- 03:45 expected completed boundaries: H4 00:00, H1 03:00, M30 03:30, M15 03:45.
- H4/H1 through 12:00 but M30/M15 stop 07:30 -> INCOMPLETE EVIDENCE.
- Future and forming rows cannot influence indicators or conclusions.

The validation record distinguishes newly executed extractor/boundary checks from analytical cases reviewed for compatibility but not re-executed against original historical evidence. Do not label a documented expected outcome as a rerun PASS. This qualification does not waive any case before changing EVALUATE logic: such a change requires a separate version, original evidence and the full regressions. V2 changes weekly analytical reporting/preference only and leaves EVALUATE logic untouched.
