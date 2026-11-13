# AUDCAD H1 BUY/SELL v1.0 — Dashboard deployment notes

Prepared 13 November 2026. Scope: implement the two frozen AUDCAD research modules on the existing dashboard, alongside other instruments. This is an implementation handover; no dashboard deployment, scheduler change, notification delivery or brokerage order has been performed.

Display label: **Frozen research baseline — not validated for live trading.** Keep BUY and SELL version identities separate. The authoritative frozen specifications are bundled with these notes. They take precedence over presentation shorthand.

## 1. Module scope

- Instrument: AUDCAD; explicitly map to the broker's actual symbol, historically AUDCAD.pro. Verify point and digits from broker metadata; do not assume another instrument's scale.
- Module IDs: `AUDCAD_H1_BUY_V1_0` and `AUDCAD_H1_SELL_V1_0`.
- Signal timeframe: completed H1. Historical parity source: complete native M30 pairs aggregated on broker-hour boundaries.
- Exit replay timeframe: M30. Each opportunity is a separate hypothetical research position.
- Broker clock throughout all user-visible timestamps. Never silently relabel broker values as local-device time. Preserve raw source timestamps and clock provenance internally.
- Add to the existing shared 15-minute refresh cycle used by other instruments, if present. Inspect the current integration before making changes; do not install duplicate schedules or replace existing modules. A quarter-hour refresh does not create quarter-hour entry signals.
- Research display only. No order routing, position sizing, automatic brokerage trading or account netting is specified.

## 2. Data and indicator contract

Use close-price recursive EMAs with `adjust=False`, alpha=2/(n+1), initialized from the first source close. Compute EMA10/12/20/26/50; EMA200 may be displayed as annotation only. MACD main=EMA12−EMA26. **MACD signal=SMA9 of MACD main, not EMA9.** Histogram=main−signal.

A usable H1 candle contains exactly two distinct M30 opens at HH:00 and HH:30, with both constituent candles complete. H1 open=first open, high=max high, low=min low, close=last close. Do not use an unfinished H1 candle or manufacture missing bars. Validate sorted/unique timestamps, prices and symbol before calculating indicators. The frozen pipeline uses consecutive observed H1 rows for previous-value comparisons; do not add a new weekend adjacency entry filter.

For exact replay parity use the bundled original source and its initialization history, starting 3-Nov-2025. For ongoing incremental computation persist the EMA state and MACD-main rolling window; do not reseed using only the visible chart range or an arbitrary trailing 200-bar window. Additional historical initialization or switching to native H1 requires a parity check before substituting it. Same timestamps with different seed history can produce different crossings.

## 3. Exact entry predicates

All conditions apply to completed H1 candle t; p denotes its preceding observed completed H1 candle.

| Condition | BUY v1.0 | SELL v1.0 |
|---|---|---|
| Fresh EMA10/50 cross | E10[t]>E50[t] and E10[p]<=E50[p] | E10[t]<E50[t] and E10[p]>=E50[p] |
| Fast EMA ordering | E10[t]>E20[t] | E10[t]<E20[t] |
| Slopes | E10, E20 and E50 each greater than their preceding value | E10, E20 and E50 each less than their preceding value |
| Price | Close[t] above E10, E20 and E50 | Close[t] below E10, E20 and E50 |
| MACD side | Main[t]>0 | Main[t]<0 |
| MACD change | Main[t]>Main[p] | Main[t]<Main[p] |
| MACD signal relationship | Main[t]>Signal[t] | Main[t]<Signal[t] |

Every row must pass. Cross equality is allowed only on the preceding bar as written. No tolerance may silently convert a failed strict condition into a pass. No requirement for E20>E50 on BUY or E20<E50 on SELL. A bullish/bearish candle body, histogram slope, EMA200 alignment or higher-timeframe agreement is not required.

Expected entry time=signal H1 open+1 hour. Benchmark entry price=the M30 opening price at exactly that time. For example H1 07:00–08:00 produces the 08:00 entry, even if dashboard processing occurs at08:15. Record both expected event time and actual detection time; do not imply the signal was shown before it was detected.

Do not substitute current quote for benchmark entry or backdate a real execution. If expected bar is temporarily not delivered, retain a data-pending signal until source availability is resolved. If confirmed absent, mark UNSCORED with reason; do not carry a weekend signal to Monday. On reconnect, backfill source events, label them historical/late, and do not present old signals as newly actionable executions.

## 4. Independent opportunity tracking

Every fresh qualifying crossing or recross creates an eligible opportunity, even when another opportunity remains open. Persistent bullish/bearish state without a new crossing creates none. There is no position cap or overlap suppression.

Track opposite-direction research opportunities independently too. An opposite signal does not close, net, reverse, or reset an existing hypothetical entry. This is two research ledgers, not a simultaneous executable account portfolio.

Suggested unique key: broker-feed identity + actual symbol + module/version + signal H1 open time. Persist it with a uniqueness constraint so repeated refreshes and retries cannot create duplicates. Store data/config revision separately; corrected source data must generate a traceable revision, not silent historical changes.

## 5. TP/SL and event resolution

AUDCAD pip=0.0001. TP60 and SL60 are price distances0.00600; on a five-digit feed these equal600points, not60points.

| Side | TP | SL |
|---|---|---|
| BUY | entry+0.00600 | entry−0.00600 |
| SELL | entry−0.00600 | entry+0.00600 |

Scan from the entry M30 bar onward. BUY target touched if high>=TP, stop if low<=SL. SELL target touched if low<=TP, stop if high>=SL. First barrier wins. If both are touched in the same first-hit M30 bar and ordering is unavailable, record AMBIGUOUS. Do not resolve optimistically or automatically discard it.

A TP hit closes only that entry. All others keep their own original entry, TP and SL. No time stop, session-close exit, opposite-signal exit, basket exit, automatic BE, trailing stop or re-entry without a new qualifying signal. Persist open entries across app restart, calendar month and weekend. At data cutoff, unresolved=OPEN. Data staleness is a separate data-quality flag, not an exit.

Store exit M30-bar open and close/availability times. The bar-open label is not the exact intrabar touch time. For strict historical parity finalize outcomes from completed M30 candles. Any partial-bar provisional observation or tick-resolved outcome must be separately labelled and must not silently overwrite benchmark semantics.

Benchmark fills are nominal barriers, without costs. Flag gap-beyond-barrier openings; do not assume improved TP fills or guaranteed SL fills. Live bid/ask quotes, actual fills and spread-adjusted scenarios must be distinct from the frozen OHLC benchmark.

## 6. Movement measures versus outcomes

Maintain two separate columns and summaries:

1. **Execution outcome:** TP60, SL60, OPEN, AMBIGUOUS or UNSCORED. Resolved win rate=TP/(TP+SL); show excluded open/ambiguous/unscored counts.
2. **Movement success:** recorded maximum favourable excursion strictly>20pips. This is not actual break-even execution. Exactly20 fails this label.

BUY favourable movement=(observed high−entry)/0.0001; SELL=(entry−observed low)/0.0001; clamp minimum to0. Restrict observation to first exit/cutoff. To reproduce archived metrics, cap TP-winner highest pips at60; stop-bar highs/lows may include prices after the unknown actual exit time. Preserve that limitation in a tooltip/notes. Do not continue accumulating highest pips after exit. A stop-out can be movement-successful and still lose60grosspips.

Prefer dashboard label **“Moved >20 pips”** rather than “BE win.” If preserving the historical “BE success” label, explain that no BE stop was executed. Show closed gross pips and open marked pips separately; optionally show their sum, clearly labelled. Month grouping is entry month, even if an exit occurs later.

## 7. Dashboard presentation

Module header: AUDCAD, H1, BUY v1.0 / SELL v1.0, frozen status, latest completed H1 timestamp, source freshness and latest refresh/detection timestamp.

Signal details: signal-bar time, entry time, direction, benchmark entry, fixed TP, fixed SL, current research status and rule-pass explanation. Show the EMA values, slopes, MACD main and SMA9 signal used at confirmation. Distinguish “no new qualifying cross” from “data unavailable.”

Entry ledger: module/version, signal time, entry time, entry price, TP, SL, status, exit-bar time, gross realized pips, open mark, highest pips, >20 flag, overlap references and data-quality indicators. Preserve every entry in chronological views and monthly exports.

Charts: H1 candles with EMA10/20/50 and optional EMA200; MACD12/26/SMA9 panel. Anchor signal markers on signal candles and entry markers on executable entry times. Show each selected entry's own TP/SL, not a shared basket level. H4/D1 or extreme overlays are optional context only.

Do not present retrospective >20 movement rates as live win probabilities. Keep BUY and SELL performance separate by default. Any combined research total is not an account equity curve without a separately specified capital/exposure model.

## 8. Suggested record fields

`module_id, rule_version, broker_feed_id, actual_symbol, source_revision, signal_bar_open, signal_available_at, detected_at, entry_time, entry_price, tp_price, sl_price, execution_status, exit_bar_open, exit_bar_available_at, gross_pips, open_mark_pips, highest_pips, movement_success, overlapping_entry_ids, gap_flag, data_quality_state, indicator_snapshot, rule_config_hash`.

Separate signal existence from execution eligibility; an UNSCORED signal must retain its reason and timestamp. Separate user-facing states from internal refresh job status. Store numeric prices with suitable precision; use integer source points for barrier comparison where possible, with broker scale validated.

## 9. Golden replay fixtures and acceptance checks

Use bundled original raw data, source metadata and BUY/SELL entry ledgers. Cutoff:12-Nov-2026 22:00 broker time, exclusive M30 open22:00; last included M30 bar21:30 closes22:00. Study entries start1-Jan-2026; original warmup starts3-Nov-2025.

| Expected benchmark | BUY v1.0 | SELL v1.0 |
|---|---:|---:|
| Executable entries |58|61|
| TP60 |30|29|
| SL60 |27|29|
| OPEN |1|3|
| Movement successes >20 |47|47|
| Movement failures |11|14|
| Additional unscored signals |0|1|
| Closed gross pips |+180|0|

SELL extra signal:18-Apr-2026 00:00 confirmation, missing expected entry bar; unscored, not a later Monday entry. BUY open position9-Nov16:00 has benchmark cutoff mark−24pips. Archived CSV files provide exact per-entry prices, outcomes and exits; aggregate matching alone is insufficient.

Required acceptance checks:

- Reproduce every BUY/SELL fixture entry timestamp, price, barrier, outcome and exit-bar label, and the highest-pips convention. Verify signal features with prefix-only data to exclude look-ahead.
- At an unfinished H1 candle, no confirmed signal. At completion, apply SMA9 MACD signal and exact strict/equality predicates.
- Same refresh repeated, worker retry and restart produce zero duplicate entries; backfill missing intervals without losing open positions.
- Fresh qualifying recross while earlier entry remains open creates another row; persistent bearish/bullish state does not.
- First entry hitting TP60 leaves second open unless its own barrier is hit. Opposite signal leaves existing entry untouched.
- +20 or +20.1 movement changes the descriptive flag only as specified; neither moves SL. ROC, CCI, Vortex, EMA200 or an extreme cannot change eligibility/exit.
- Correct600point distances on five-digit AUDCAD; reject a symbol-scale mismatch rather than silently using another instrument's constants.
- Missing entry bar, duplicate candle, stale feed, revised source and ambiguous same-bar barriers remain explicit; no guessed fills.
- Entry-month summaries preserve open trades across months and distinguish actual outcomes from movement labels.

## 10. Integration sequence and rollback

First inspect existing module interfaces, feed clock, scheduler, state store and rendering conventions. Implement AUDCAD modules and persistence behind a feature flag. Run golden replay and focused acceptance checks. Then expose a paper/research view with source freshness and record late discovery times. Integrate into the existing shared refresh job without changing unrelated instruments. No external notifications or brokerage orders are part of this handover.

For rollback disable new AUDCAD evaluation/display through its feature flag, preserving persisted research history and immutable frozen specifications. Do not delete original fixtures or replace other instruments' modules. Source revisions or execution-cost enhancements require explicit separate versioning and comparison. No production integration has been verified by preparing these notes.
