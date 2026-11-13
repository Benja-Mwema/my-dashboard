# AUDCAD H1 BUY — Frozen research baseline v1.0

Status: FROZEN by user instruction on 13 November 2026. This version preserves the original BUY v0.1 entry, exit, overlap and accounting rules without modification. It does not incorporate any experimental break-even variant, including ROC-gated BE. SELL v1.0 remains frozen and unchanged. Future modifications must receive separate version identifiers and be compared with this baseline. Freezing records the specification; it does not constitute independent validation or live deployment.

## Instrument, clock and indicators

AUDCAD (broker symbol AUDCAD.pro). H1 signals using completed H1 candles reconstructed from complete M30 pairs; broker timestamps preserved. No unfinished candle inputs. Close-price EMA10, EMA20, EMA50. MACD main=EMA12−EMA26; MACD signal=SMA9 of MACD main (not EMA9). Recursive EMAs use adjust=False, alpha=2/(n+1), initialized from first available source close; retain and disclose historical warmup as in SELL baseline.

## BUY entry — all conditions on completed H1 candle t

1. Fresh upward EMA10/EMA50 cross: EMA10[t]>EMA50[t] AND EMA10[t−1]<=EMA50[t−1].
2. EMA10[t]>EMA20[t].
3. EMA10[t]>EMA10[t−1], EMA20[t]>EMA20[t−1], AND EMA50[t]>EMA50[t−1].
4. Close[t]>EMA10[t], Close[t]>EMA20[t], AND Close[t]>EMA50[t].
5. MACD main[t]>0.
6. MACD main[t]>MACD main[t−1].
7. MACD main[t]>MACD signal[t].

All comparisons are strict except the preceding-bar <= test in condition1. No extra requirement for EMA20>EMA50, rising MACD histogram, bullish candle body, H4 alignment or a prior extreme.

Enter BUY at the next M30 opening price at H1 completion time. Record signal candle-open and entry time separately. If that expected entry bar is unavailable, mark unscored/non-executable rather than carrying the signal to a later session. All inputs must have been available by entry time.

## Repeated signals and overlaps

Every fresh qualifying upward EMA10/50 crossing or recross is eligible. Remaining bullish alone creates no new entry. A later qualifying signal is allowed if an earlier entry was missed or is still open. Preserve all qualifying overlaps, with no one-position restriction or two-position cap. Each is an independent opportunity. This rule does not introduce a combined BUY/SELL portfolio or netting policy; evaluate BUY separately from SELL. An opposite signal is not an exit instruction.

## Independent TP60/SL60

For each BUY entry price P:

- TP=P+0.00600, 60pips above entry.
- SL=P−0.00600, 60pips below entry.
- AUDCAD pip=0.0001; 60pips=600points on the five-digit source.
- In M30 OHLC evaluation, high>=TP touches the target; low<=SL touches the stop. Start with the entry bar and scan chronologically.
- Resolve each position independently at its first barrier. One entry reaching TP60 closes only that entry; others keep their own original TP/SL.
- No time cutoff, session-close exit, opposite-signal exit, basket exit, trailing stop or automatic break-even stop.
- If both barriers are touched within the same first-hit M30 bar with unknown order, report AMBIGUOUS rather than inventing the sequence.
- If neither barrier is reached by source cutoff, report OPEN, not LOSS.

## Accounting and research labels

Preserve the SELL benchmark convention: next-M30 OHLC open entry and nominal barrier fills, excluding spread, commission and slippage. Flag openings beyond a barrier; do not silently claim improved fills. Spread is diagnostic, not a threshold filter. Any cost-aware execution model must be separately versioned.

Actual outcomes: TP60=+60grosspips, SL60=−60grosspips, OPEN remains unrealized, AMBIGUOUS unscored. Group months by entry time; later exits remain attached to their original entry.

User movement classification remains separate: favourable BUY movement is upward from entry; recorded maximum excursion strictly>20pips is movement success, including an OPEN case. TP60 is a win. The >20and<60 “BE” label is descriptive, not an implemented break-even stop. Exactly20 is not success; an exactly60 excursion without an unambiguous TP outcome must retain its execution uncertainty. Preserve baseline maximum-excursion accounting: TP winners capped60, other excursions limited to exit/cutoff observations. M30 exit-bar extrema can contain prices after the barrier touch; disclose this limitation, particularly for stop-outs and ambiguous bars. These labels must not be presented as realized trading profit.

## Research boundaries and excluded changes

EMA200 filters, H1/H4 extremes, multi-timeframe indicator filters, session conditions, delayed confirmations and fitted failure filters remain annotations or separate experiments. None is an additional entry requirement. No BE10/20/30/40, ROC-gated BE, indicator-gated BE or structure-gated BE is included. Reaching more than20 favourable pips does not move the stop.

## Archived baseline results

January–12 November 2026, ending22:00 broker time:58 executable entries,30TP60,27SL60,1OPEN. No ambiguous or unscored signals. Resolved TP rate30/57=52.6%; closed gross+180pips, open mark−24pips, total marked+156pips before costs under equal-size accounting. Movement successes47/58=81.0%, including16actualSL exits andoneOPEN;11movement failures. These are exploratory historical results, not unseen validation. All overlaps retained. No re-backtest or altered performance is implied by this freeze.

## Provenance

Source: AUDCAD_H1_BUY_Research_Rule_v0_1.md, created13November2026, mirrored from frozen SELLv1.0. Implementation and outcomes: audcad/run_buy_jannov_v0_1.py and audcad/buy_jannov_v0_1/all_cases.csv. Original source/warmup preserved (3-Nov2025 start); native-history research annotations with longer warmup do not redefine these entries. Prior files remain unchanged. This document is the authoritative BUYv1.0 frozen specification.

Original v0.1 specification SHA256: 03e56cf9ba6596d8c21fa2edb8a42d7ec2ea31f8372fe3e6fb35b554461fa3f1
