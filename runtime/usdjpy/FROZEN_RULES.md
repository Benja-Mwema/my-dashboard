# USDJPY H1 E1 v0.2 — Frozen research baseline

Created 18 November 2026 at the user's direction to use H1 EMA10/20/50, extract data and unfreeze the working formula.

**Status: FROZEN RESEARCH BASELINE.** `frozen: true`, `editable: false`. Frozen and authorized for dashboard publication by the user on 18 November 2026. Rule changes require a new version. Performance validation is pending. The parent M30 E1 v0.1 rule and implementation are preserved in `previous_M30_v0_1/` for comparison. The parent document described a candidate research specification; no separate frozen USDJPY production specification was established by the located files.

## Formula basis

Instrument: native MT5 `USDJPY.pro`, server `SCFMLimited-Live2`. All cluster, direction, slope and candle calculations use **completed H1 candles**. The EMAs are **10, 20 and 50**, calculated from H1 closes. This is native H1 extraction, not M30 aggregation.

At each completed H1 candle t:

- EMA(n,t) = [2/(n+1)] Close(t) + [1−2/(n+1)] EMA(n,t−1), n = 10, 20, 50. Seed each EMA with the first warm-up close.
- TR(t) = max(High−Low, |High−previous Close|, |Low−previous Close|). The first TR is High−Low.
- ATR14(t) = TR(t)/14 + 13 ATR14(t−1)/14; seed with the first TR.
- W(t) = max(EMA10, EMA20, EMA50) − min(EMA10, EMA20, EMA50).
- **Cluster / convergence: W(t) / ATR14(t) ≤ 0.50**, with positive ATR.
- S(n,t) = [EMA(n,t) − EMA(n,t−3)] / [3 ATR14(t)]. The four bars must be consecutive hourly candles.
- CL(t) = [Close−Low]/[High−Low]. A zero-range candle cannot confirm.
- UpCloses3 and DownCloses3 count strictly positive/negative close changes across the last three transitions. LowerPairs3 counts transitions where both high and low are strictly lower.

## Confirmation formula

All conditions in the relevant column must be true on the same completed H1 candle.

| Condition | BUY | SELL |
|---|---|---|
| Known consecutive cluster duration N | 2–8 H1 candles | 4–16 H1 candles |
| EMA order | EMA10 > EMA20 > EMA50 | EMA10 < EMA20 < EMA50 |
| Three-bar slopes | S10 > 0, S20 > 0, S50 ≥ 0 | S10 < 0, S20 < 0, S50 ≤ 0 |
| Expansion | W(t) > W(t−1) | W(t) > W(t−1) |
| Price beyond band | Close > EMA10 | Close < EMA10 |
| Candle direction | Close > Open | Close < Open |
| Candle finish | CL ≥ 0.50 | CL ≤ 0.50 |
| Price progression | UpCloses3 ≥ 2 | DownCloses3 ≥ 2 and LowerPairs3 ≥ 2 |

EMA10/20 must therefore be positioned in the formation's direction. This version does not add a requirement for a fresh crossover on the confirmation candle or within a specified crossover-age window. EMA50 ordering remains part of the inherited E1 definition.

## Episode and causal timing

1. A new cluster starts when W/ATR first qualifies after a nonqualifying bar or a timestamp gap. Its known length starts at one.
2. Evaluate during the cluster and once on its first continuous outside candle, using only the duration and minimum width known at that time.
3. Only the first passing BUY or SELL consumes the episode. At most one formation is recorded per episode.
4. An episode expires after its first outside candle. A gap immediately invalidates the old episode; the post-gap candle can begin a new cluster.
5. Confirmation uses only completed H1 candles. Signal time is the candle's open timestamp plus 3,600 seconds. It must not be backdated to cluster start.
6. A research next-open price is available only if the next native candle opens exactly 3,600 seconds later. Otherwise it is cancelled for a gap, or pending at the end of the source. These are gross price proxies, not executable fills.
7. There are no added H4, session, weekday, range-break, stop, target or position-sizing rules in this version.

## What changed from M30

- Timeframe: M30 → H1 for all indicator, cluster and confirmation calculations.
- Continuity and next-open interval: 1,800 → 3,600 seconds.
- Three-transition continuity: 5,400 → 10,800 seconds.
- EMA periods remain 10/20/50; ATR period remains 14; width threshold remains 0.50 ATR.
- Persistence settings remain 2–8 BUY bars and 4–16 SELL bars. They now represent H1 bars and therefore twice the uninterrupted elapsed duration of the M30 version. They were not optimized or rescaled to preserve the old elapsed time.
- The H1 formula is now frozen as a research baseline, with performance validation pending.

The old M30 performance must not be assigned to this H1 version. H1 profitability, robustness and predictive value remain unmeasured. If the inherited 12/24-bar outcome study is later run, those horizons would correspond to 12/24 H1 candles, with gaps reported; no such outcome evaluation is included here.

## Data extracted and checks

Snapshot: 18 November 2026. Extracted 7,048 raw native H1 bars from 1 October 2025 through the forming 18 November 2026 15:00 bar. Excluded that forming bar from indicator evaluation and formation generation.

- Completed candles: **7,047**.
- Warm-up: **1,560** candles before 2026.
- 2026 analysis: **5,487** completed candles.
- Latest evaluated candle: **18 November 2026 14:00**, known at its **15:00 close**, native broker labels.
- Formations in 2026: **55**, comprising **34 BUY** and **21 SELL**.
- Observed cluster episodes intersecting 2026: **141**.
- No duplicate timestamps, invalid OHLC or off-hour timestamps.
- 61 timestamp gaps across the full extraction are listed in `data_audit.json`; no gaps are filled. This includes market closures and is not a claim that every gap is a feed defect.
- Independent episode scan agrees exactly; 18 historical-prefix checks confirm that later bars do not change earlier indicators or formations; one-formation and gap-continuity checks pass.

Raw epochs are preserved. Display labels use the existing native-source convention without a timezone shift. Historical broker DST/UTC offsets were not independently verified; these labels should not be relabelled EAT or UTC.

## Files and reproduction

The production research module is `C:\Ben\mt5\aurum_cluster_v2\usdjpy`. The frozen research copy is `C:\Ben\mt5\research\USDJPY_H1_E1_v0_2_FROZEN_20261118`.

- `formula.py` and `formula_config.json`: frozen H1 calculations and parameters.
- `build_snapshot.py`: read-only MT5 refresh, native-history verification and dashboard adapter.
- `freeze_manifest.json`: hashes of the frozen formula, parameters, adapter, specification and baseline inputs.
- `reference/native_source.json`: captured baseline source, including a separately excluded forming candle.
- `reference/formations.csv`: the 55 accepted baseline formation records.
- `reference/unfrozen_formula.py` and `reference/unfrozen_config.json`: preserved pre-freeze versions.
- `site/usdjpy-replay.json`: immutable baseline dashboard evidence.
- `site/usdjpy-data.json`: latest refreshed dashboard evidence, including completed candles and their model indicators.
- `site/usdjpy-acceptance.json`: baseline and causal verification results.
- `site/usdjpy-rules.json`: published frozen parameters and hashes.
- `config.json`: enabled, paper-only deployment configuration; broker orders disabled.

From the runtime module directory, run `python build_snapshot.py --offline` to reproduce the frozen baseline or `python build_snapshot.py` to refresh from the authorized Windows MT5 session. Python, NumPy and the MT5 package are required for native refresh; the offline path requires NumPy only. Baseline files are never overwritten by the refresh adapter. Source OHLC revisions stop USDJPY publication and retain the previous verified snapshot; other instruments continue.

The existing 15-minute dashboard refresh includes USDJPY. This deployment does not enable USDJPY email notifications or live-order execution. Performance evaluation remains pending. Rule changes require a new version.
