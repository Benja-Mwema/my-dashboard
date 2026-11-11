# GBPJPY H1 R1 v1.0 — frozen dashboard module

Entry version: GBPJPY_H1_R1_v1.0. Evaluation version: GBPJPY_H1_EMA_TOUCH_v1.0.
Frozen research baseline — not validated for live trading.

The entry module implements the frozen rule without added filters. Source EMA seed is the first saved close on 3 August 2026. Broker clock values are formatted without timezone conversion. C2 close is a reference, never a fill. Pip = 0.01. Deduplication identifier includes version, broker symbol, H1, C0 opening timestamp. Rebuilding snapshots is deterministic; live touches persist by that identifier independently of candidates.

## Reproduce

`python -m unittest discover -s . -p "test_*.py"`

`python gbpjpy_r1.py` writes the frozen replay. Expected: 15 signals / 14 modeled touches / 1 open / 6 nonnegative / 8 negative / 42.8571% / +181.930303198 gross pips. Tests compare each entry and exit reference with archived evidence, not only aggregate totals.

## MT5 observation

Runtime: C:\Ben\mt5\aurum_cluster_v2\gbpjpy

`C:\Ben\mt5\.venv\Scripts\python.exe refresh_gbpjpy.py` performs one snapshot and tick observation.

`C:\Ben\mt5\.venv\Scripts\python.exe refresh_gbpjpy.py --watch` continuously reads ticks; no trading API calls. A lock prevents duplicate watchers. Stop with Ctrl+C. If an ungraceful shutdown leaves observer.lock, verify its PID is no longer running before removing it. This is an interactive process, not a Windows service or boot-persistent task.

Each loop retrieves ticks since its prior tick cursor. Observed equality/crossing is evaluated against EMAs of the preceding completed H1 bar, never accumulated recursively per tick. Only the first captured event is retained per signal. A late observer cannot prove the first market touch; that limitation is stored with the event. observed_touches.json is a persistent local journal. Historical OHLC fills observation gaps with MODELED references, never fabricated observed ticks. Opening already crossed uses the open reference; intrabar equality uses the solved touch level. Exact intrabar timing is unavailable from OHLC.

The observer updates local gbpjpy-data.json every 30 seconds. The Render dashboard is static: it displays the most recently published snapshot, not a live stream. To publish fresh data, run tests, copy the generated data file to the repository root, commit only that file, and push the established main branch. Never overwrite the frozen replay. Browser reload does not contact MT5. The page labels this distinction and suppresses directional arrows for stale snapshots.

Observed touches retain their own reference and modeled outcomes remain separately recorded. No executed prices are supplied. All P/L is gross; costs are not deducted. Open outcomes are excluded from the completed denominator. MFE/MAE use complete candles before the first touch plus its reference, excluding unknown pre/post-touch extrema within the exit hour. They are conservative OHLC measurements, not exact tick excursions.

## UI and integration

GBPJPY has a dedicated gbpjpy.html module reached from AURUM's instrument selector. Other instrument engines are unchanged. The frozen replay is the default view; latest observation is a separate option. Solid price paths are actual recorded H1 closes; modeled touch markers do not imply observed prices. An active direction symbol, when present, is outside price/time axes and explicitly not a forecast. No target, horizon, confidence, SL, TP or extra research filter is supplied.

Source artifacts: GBPJPY_H1_R1_Application_01Oct_09Nov2026.zip and GBPJPY_H1_R1_First_Touch_Exit_01Oct_09Nov2026.zip from the frozen research. Original definitions in FROZEN_RULE.md; exact input in frozen_bars.json; archived expected ledgers in expected_signals.json and expected_touches.json.
