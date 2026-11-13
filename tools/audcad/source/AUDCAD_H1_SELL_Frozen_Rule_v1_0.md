# AUDCAD H1 SELL — Frozen research baseline v1.0

Status: FROZEN by user instruction on 13 November 2026. This records the existing v0.3 baseline without changing entry, exit or overlap behaviour. Subsequent variants must use separate version identifiers and be compared against this baseline. Freezing does not constitute predictive validation or live-trading deployment.

## Instrument, clock and indicators

- AUDCAD (broker symbol AUDCAD.pro). H1 signal timeframe; broker timestamps preserved.
- Use completed H1 candles, reconstructed from complete M30 pairs in the existing research implementation. No unfinished candle inputs.
- Close-price EMA10, EMA20, EMA50; MACD main = EMA12 minus EMA26; MACD signal = simple moving average of the latest 9 MACD-main values, NOT EMA9.
- EMAs use recursive adjust=False calculation, alpha=2/(n+1), initialized from the first available source close. Retain historical warmup before evaluating the requested period. Historical results remain tied to their archived source/warmup; changing initialization/history must be disclosed.

## Entry: all conditions required on completed H1 candle t

1. Fresh EMA10/EMA50 downward cross: EMA10[t] < EMA50[t] and EMA10[t−1] >= EMA50[t−1].
2. EMA10[t] < EMA20[t].
3. EMA10[t] < EMA10[t−1], EMA20[t] < EMA20[t−1], and EMA50[t] < EMA50[t−1].
4. Close[t] below EMA10[t], EMA20[t], and EMA50[t].
5. MACD main[t] < 0.
6. MACD main[t] < MACD main[t−1].
7. MACD main[t] < MACD signal[t].

Enter SELL at the next M30 opening price at H1 completion time. Signal-bar time and executable entry time must be recorded separately. If the expected M30 entry bar is unavailable (e.g. weekend), classify the signal as unscored/non-executable; do not silently carry it into a later session.

Every new qualifying crossing or recross is eligible. Persistent bearishness without a fresh EMA10/50 cross does not create another entry. A later qualifying signal is allowed if the first was missed or remains open. Preserve all overlaps; no one-position restriction or two-position cap.

## Independent exits

For each entry price P:

- TP = P − 0.00600 (60 pips).
- SL = P + 0.00600 (60 pips).
- AUDCAD pip = 0.0001; on the five-digit source 60 pips = 600 points.
- Each entry closes only at its own TP or SL. First entry reaching TP60 does not close the second; the second retains its original barriers.
- No time cutoff, session-close exit, opposite-signal exit, basket exit, trailing stop or automatic break-even stop.
- Observe to first barrier or available-data cutoff. Unresolved at data cutoff = OPEN, not LOSS.
- If both barriers occur within the same M30 bar and ordering is unknown, label AMBIGUOUS; do not guess.

## Research accounting and excluded filters

Current OHLC benchmark assumes nominal barrier fills without spread, commission or slippage deductions. Preserve gap-beyond-barrier flags. Spread remains a diagnostic annotation; no fixed spread threshold or new execution adjustment is introduced by this freeze. Cost-aware execution variants must be separately versioned.

H1/H4 extremes, H4 EMA/MACD alignment, session labels, rebound descriptors, delayed-confirmation variants and fitted failure filters are research annotations only. None adds to the entry conditions above.

Report actual TP/SL/OPEN outcomes separately from the user's movement-success classification. A recorded favourable excursion strictly greater than20 pips counts as movement success; TP60 counts as a win; open entries above20 maximum favourable pips also count as movement successes. The historical “BE success” label does not implement a break-even stop or imply a profitable executed trade. Exactly20 is not greater than20. Historical highest-pips values were capped60 for TP winners; stop-bar extrema may include after-exit prices. Preserve these limitations when comparing archived results.

## Archived baseline reference

January–12 November2026 study:61 executable entries,29TP,29SL,3OPEN;47movement successes and14unsuccessful under the recorded classification. One additional weekend signal18-Apr2026 00:00 remained unscored. November cutoff12-Nov2026 22:00 broker time. These are historical exploratory results, not independent validation. No re-backtest or performance change is implied by freezing.

Source specification: audcad/jannov_research/RULE.md (previously draft v0.3); implemented trigger in audcad/jannov_research.py. Prior studies and source files remain unchanged. This document is the authoritative v1.0 frozen specification.
