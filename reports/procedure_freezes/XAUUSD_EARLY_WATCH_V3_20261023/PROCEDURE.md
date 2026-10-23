# XAUUSD Early-Watch Overlay V3

**Method ID:** `XAUUSD_EARLY_WATCH_V3_20261023`
**Status:** Frozen prospective research candidate; not approved for live entry use.
**Frozen:** 23 October 2026, 08:04:45 EAT.
**Parent:** `XAUUSD_WEEKLY_PROCEDURE_V2_20261021`
**Scope:** Add a request-driven early-watch state to the existing weekly-map and EVALUATE workflow. V1 and V2 are unchanged.

## 1. Purpose and boundaries

V3 tests whether M15 can alert Codex and the user to a developing setup before all higher-timeframe entry gates align. An early alert means **watch/prepare only**. It is not a trade recommendation, an entry verdict, or permission to bypass a full EVALUATE.

For each target week, V3 uses the exact V2 weekly map, its levels, route directions, activation conditions and failures. V3 does not generate a second set of weekly levels or change the weekly preference. Keep the existing V1/V2 prospective study intact; V3 has a separately registered overlay study. Do not change the accepted Python extractor, its causal filters, output fields, indicator formulas, EVALUATE prompts, verdict taxonomy, or the frozen 65% / 2.5 ATR thresholds.

Python supplies completed-bar facts and numerical metrics only. Codex decides whether the active scenario is valid, whether the M15 pattern qualifies and triggers under this protocol, whether any higher-timeframe gate is satisfied, and the user-facing interpretation. Python must not emit a BUY/SELL, permission, confirmation, invalidation, no-chase verdict, or this method's alert decision.

## 2. Request-driven review and causal time

No background polling, automation, or unscheduled forecast updates are part of V3. Evaluate only when the user requests a DAILY or EVALUATE review. At each request, use the latest validated evidence at that requested cutoff and retain only bars whose `close_time` is at or before it. A forming bar cannot qualify, trigger, expire, confirm, or invalidate an event.

When a prior V3 review exists, Codex may reconstruct the bars since that review to identify the first intervening M15 event, but must also determine whether it is still active at the current requested cutoff. Report both the event's actual completed `close_time` and the current evaluation cutoff. If no prior review exists, search only from the forecast's actual valid-from time. Never backdate an alert to before the frozen forecast existed. Material M15/M30 incompleteness returns `INCOMPLETE EVIDENCE` under existing rules.

Every record is tied to one forecast ID, one frozen weekly map, one route, one direction, and one user-requested cutoff. Primary and alternate routes are evaluated separately. The alternate is eligible only after Codex verifies its frozen activation requirements; a primary failure alone does not silently make the alternate active.

## 3. Early-watch states

These are V3 observation states, not EVALUATE verdicts:

1. **MAP WATCH** — price has interacted with the active frozen origin, but no valid M15 qualification has completed.
2. **M15 QUALIFIED** — the exact qualification condition below has completed; the next directional trigger is awaited.
3. **EARLY WATCH — TRIGGERED** — the subsequent M15 trigger has completed, the route remains active, the objective is unconsumed, and the provisional room screen passes. This is an attention alert only.
4. **FULL GATES PENDING** — M30, H1, H4 or the final no-chase evaluation is not yet fully satisfied. Name each pending or conflicting gate.
5. **FULL EVALUATE REQUIRED** — if all gates appear aligned, run the existing EVALUATE workflow at the requested cutoff. Only that workflow may return an allowed-entry verdict.
6. **LAPSED / EXPIRED / ROUTE FAILED / OBJECTIVE ALREADY REACHED / PROVISIONAL ROOM FAIL / INCOMPLETE EVIDENCE** — explain the cause and event time. These are V3 journal statuses, never substitute verdicts.

Never display `EARLY WATCH — TRIGGERED` as `BUY`, `SELL`, `BUY ALLOWED`, or `SELL ALLOWED`. On any dashboard or written report, show the early-watch state in a separate field from the official EVALUATE verdict.

## 4. M15 qualification and trigger

Use the active route's frozen origin zone and direction. The qualifying M15 candle must be fully completed after `valid_from`, must intersect the origin zone, and must close beyond the far boundary in the route direction:

- BUY: candle range intersects the origin; close is above the origin's upper boundary.
- SELL: candle range intersects the origin; close is below the origin's lower boundary.

The M15 MACD histogram must improve directionally on that completed qualification candle versus the immediately preceding completed M15 candle: current histogram greater than the prior value for BUY, lower for SELL. Codex verifies the values and their meaning; no automated signal label is allowed. Candle body color is not a separate requirement. This resolves the V2 phrase “directional indicator improvement” for this V3 overlay only; it does not rewrite V2 or earlier frozen forecasts.

The trigger is the first later completed M15 candle that closes above the qualification candle's high for BUY or below its low for SELL. The qualification and trigger must belong to the same active route and precede any route failure or first-objective contact. If the order is ambiguous within a single bar, do not infer it from OHLC; use finer verified evidence or report unresolved.

## 5. Trigger lifecycle and expiration

At the trigger close, record the event as `EARLY WATCH — TRIGGERED` only if all of these are true: the frozen route is still active; its alternate activation (if applicable) is established; its first opposing objective has not already been reached; neither frozen route invalidation has occurred; data is complete; and the provisional room screen below passes.

The early alert lapses at the earliest completed event among:

- A completed M15 close through the opposite extreme of the qualification candle (BUY: close below qualification low; SELL: close above qualification high).
- The route's frozen failure condition, confirmed on its specified timeframe.
- Contact with the route's first objective before full confirmation. The first-leg opportunity is then consumed; a later setup requires a new timestamped assessment and a fresh M15 qualification/trigger, and cannot revive the old alert.
- The end of the forecast's frozen validity period.

At every requested cutoff, re-check all lifecycle conditions using completed evidence. An old trigger is not active merely because it once occurred. If an invalidation and target are both inside one OHLC candle and their order is unknown, report chronology unresolved; do not award target-before-failure credit.

## 6. Provisional no-chase screen and full entry

V3 performs a **provisional** room screen at the M15 trigger using the qualification candle's low as BUY turn reference or high as SELL turn reference, and the near edge of the nearest still-unconsumed opposing frozen zone as the objective. Use the same arithmetic and strict thresholds as the existing no-chase rule:

- projected leg is positive and defined;
- projected leg consumed is strictly below 65%;
- remaining distance is at least 2.5 times the M15 ATR available at the trigger close.

If any input is missing, nonpositive or ambiguous, mark the provisional screen `NOT CALCULABLE` and do not issue a triggered early alert. If either threshold fails, record `PROVISIONAL ROOM FAIL`; the route may remain under observation, but V3 must not imply a fresh entry. This screen never authorizes a trade.

At full EVALUATE confirmation, recalculate no-chase from the exact confirmation-time price, turn reference, nearest unconsumed objective and M15 ATR at that time. Do not carry forward a provisional PASS. The existing simultaneous-gate requirement remains unchanged: H4 allows, H1 permits, M30 confirms, M15 qualifies/triggers, the forecast is valid, and both full no-chase tests pass. A zone touch or early alert alone remains non-entry evidence.

## 7. Request-time report fields

Every V3 review records: method ID; forecast ID and map hash; route and direction; requested cutoff; latest completed boundaries and completeness; current route lifecycle; qualification and trigger bar-open and close times; OHLC and required histogram values; trigger age in completed M15 bars; lapse/expiry condition if any; nearest unconsumed objective; provisional room inputs/results; H4/H1/M30 gate state with evidence times; whether full EVALUATE was requested/completed; official EVALUATE verdict if completed; and any missing evidence. Use `early_watch_record.template.json`.

State facts, Codex judgments, and official verdict separately. Preserve every requested review including no-alert, lapsed, blocked and incomplete outcomes. Do not invent observations for days when no update was requested.

## 8. Prospective evaluation

The 20 weeks from 26 October 2026 through 12 March 2027 are a planned prospective test window, registered separately in `output/weekly_prospective_v3_early_watch_20261026_20270312/STUDY_PROTOCOL.json`. The V2 weekly map remains the map under test; V3 adds the early-watch overlay. The historical 1 June–16 October 2026 replay is development material only and cannot validate V3.

At each requested review, score the event lifecycle without treating alerts as trades. Record: eligible requested reviews; evidence completeness; weeks/routes with no request coverage; early triggers; provisional room passes/fails; lapsed alerts and cause; time from early trigger to full confirmation when it occurs; full confirmation/no-chase verdict; first objective before route failure, route failure first, neither by expiry, or chronology unresolved; and adverse excursion from the trigger and from full confirmation. Report denominators at event, route, week, and requested-review level. Also report weeks with no eligible observation separately; do not call missing coverage a no-signal week.

V3 may be judged useful for earlier awareness only if it provides earlier active alerts before full confirmation without increasing misleading/expired alerts beyond an explicitly reviewed tolerance. Since requests are user initiated and may be sparse, alert recall and untouched/missed setups are **UNSCORED** unless review coverage is sufficient to establish them. Do not claim win rate, profitability, fill quality, or predictive accuracy from target contact. A 20-week sample is small; V3 remains research-only after the test unless a separate documented promotion decision is made.

Do not edit the frozen V1/V2 study protocol to add V3. Keep V3 records in its separate study directory. A combined comparison may be made only where the V1/V2 and V3 records have the same preweek evidence, target week, cutoff, map, and eligibility; identify missing pairs and protocol differences.

## 9. Preservation and compatibility

V3 does not edit or replace `AGENTS.md`, the accepted extractor, `prompts/weekly.md`, `prompts/daily.md`, `prompts/evaluate.md`, V1, V2, the current live weekly levels, AURUM, or Render. Existing EVALUATE statuses and all accepted regression cases remain controlling. Any future change to V3 rules must create a new version and a fresh prospective block; never tune this frozen candidate in place.
