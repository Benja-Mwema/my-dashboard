# GBPJPY H1 R1 — Two-Candle EMA Expansion

**Status: FROZEN — research entry-signal baseline**
**Version: 1.0**
**Freeze date: 10 November 2026 (Africa/Kampala)**
**Authority: user instruction “freeze R1”.**

This freeze applies only to GBPJPY H1. It does not modify XAUUSD rules or earlier GBPJPY rejection-zone research. It does not authorize live trading or constitute independent validation.

## 1. Inputs and clock

- Instrument: GBPJPY; study feed GBPJPY.pro.
- Timeframe: native H1 candles, completed bars only.
- EMA10 and EMA20 calculated from closing prices with alpha = 2/(period+1), recursively: EMA[t] = alpha × close[t] + (1−alpha) × EMA[t−1].
- Baseline reproduction uses the first saved close on 3 August 2026 as the seed and retains all subsequent warm-up bars. Preserve this history when reproducing the frozen sample; do not restart indicators on 1 October.
- Broker timestamps are retained without conversion. A candle labelled 03:00 becomes available at 04:00 when completed. Do not use its final values before then.
- One pip = 0.01 JPY = ten broker points on the three-decimal study feed.

## 2. Exact signal rule

Let g[t] = EMA10[t] − EMA20[t]. C0 is a completed crossover candle. C1 and C2 are its immediately following H1 candles.

| Requirement | BUY | SELL |
|---|---|---|
| C0 crossover | g[C0−1] ≤ 0 and g[C0] > 0 | g[C0−1] ≥ 0 and g[C0] < 0 |
| C1 ordering | g[C1] > 0 | g[C1] < 0 |
| C1 EMA slopes | EMA10[C1] > EMA10[C0] and EMA20[C1] > EMA20[C0] | Both inequalities reversed |
| C1 gap expansion | abs(g[C1]) > abs(g[C0]) | Same |
| C2 ordering | g[C2] > 0 | g[C2] < 0 |
| C2 EMA slopes | EMA10[C2] > EMA10[C1] and EMA20[C2] > EMA20[C1] | Both inequalities reversed |
| C2 gap expansion | abs(g[C2]) > abs(g[C1]) | Same |

All conditions must pass. Comparisons use full-precision EMA values, not displayed rounded numbers. Equality at either continuation checkpoint is not a pass; an equal EMA pair on C0 is not a directional crossover. No tolerance or minimum gap is added.

C0, C1 and C2 must have consecutive broker opening timestamps exactly one hour apart. A missing candle or weekend gap invalidates this candidate; do not synthesize bars.

## 3. Entry timing and candidate lifecycle

- The earliest research entry decision is immediately AFTER C2 closes.
- C2 close is the historical reference price, not a guaranteed executable fill. A future execution study must record the available bid/ask, spread and slippage separately.
- If C1 or C2 fails, reject that crossover. Do not roll the window forward until two later candles happen to pass.
- A fresh opposite crossover begins a new assessment. The same completed candle can invalidate the old candidate and establish a new C0 in the opposite direction.
- Emit at most one R1 signal per crossover. Continued expansion after C2 is not a repeated entry signal.
- If C2 has not closed, the candidate remains pending; it is not an accepted signal.

Example: the 2 November 2026 UP crossover is on the 01:00 candle. The 02:00 and 03:00 candles pass C1 and C2. The decision becomes available at 04:00 broker time. The C2 reference close is 211.264.

## 4. Explicitly outside R1

The following are NOT entry requirements: a six-candle price-range breakout; price closing progressively higher/lower on every candle; a minimum crossover body; EMA50 or EMA200 alignment; an absence of recent whipsaws; a session restriction; an opposing-zone or remaining-room threshold; an ATR-distance cap; MACD or other indicator qualification.

Distance already travelled and previously identifiable opposing zones may be recorded as diagnostics, but must not silently reject or alter R1 signals.

Stop-loss, take-profit, position sizing, simultaneous-position handling and trade exit rules are UNDEFINED in R1. This is an entry-signal research rule, not a complete trading strategy.

## 5. Frozen exploratory evidence

Sample: 1 October–9 November 2026 inclusive. Original source: 672 H1 window bars, plus saved warm-up history. There are 31 completed new crossover clusters, one inherited cluster (G01) and one unfinished cluster (G33). G01 and G33 are excluded from the completed-cluster evidence below.

For descriptive outcome classification, measure maximum favourable movement from the crossover close through the next opposite crossover close. Exclude the crossover candle's earlier high/low; include the next opposite crossover candle because the change becomes confirmed at its close.

| Outcome | All completed clusters | Accepted by R1 |
|---|---:|---:|
| Strong: at least 100 pips MFE | 6 | 6 |
| Moderate: 50 to under 100 pips MFE | 6 | 6 |
| Weak: under 50 pips MFE | 19 | 2 |
| Total | 31 | 14 |

Accepted cluster IDs: G02, G03, G05, G07, G08, G11, G12, G13, G14, G15, G16, G21, G27, G32. All fourteen accepted cases have consecutive hourly C0–C2 candles.

Strong original clusters: G07, G08, G15, G16, G27, G32. Known accepted weak cases: **G03 and G05**. Retain them in every reproduction and comparison.

Measured from AFTER C2 close rather than from the original crossover, 9 of 14 accepted clusters retain at least 50 pips MFE and 5 of 14 retain at least 100 pips MFE. G03 retains 21.8 pips and G05 only 4.9 pips. These are favourable excursions, not target-before-stop win rates or realized profit. No costs are deducted.

These dates and their outcomes were already inspected when the candidate was selected. This is in-sample exploratory evidence. The 12/14 original-movement classification must not be called an 85.7% trading win rate.

## 6. Version control and future validation

Preserve this v1.0 rule and its failures unchanged. Any change to conditions, thresholds, timing, filters or indicator conventions requires a separately named version and an explicit comparison against R1 v1.0. Record data corrections separately; do not silently replace the source snapshot.

Further validation must apply the frozen rule to untouched historical dates or prospective paper observations. Evaluate remaining movement and adverse excursion from the actual decision time. Do not credit pre-entry movement to R1. Keep original exploratory results separate from new validation results.

## 7. Evidence references

- Baseline: GBPJPY_H1_EMA10_20_Clusters_01Oct_09Nov2026.html — Library ID libfile_9c4ae6ad4c1c8191b168da5480a97463.
- Formation evidence, source snapshot and calculations: GBPJPY_H1_Formations_01Oct_09Nov2026.zip — Library ID libfile_eefd1e82636081918a60a91e7e3f4e47.
- The earlier six-bar price-range walkthrough is a separate exploratory method and is not the R1 entry rule.
