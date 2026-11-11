# AURUM cluster dashboard — H1-P1 v2.0 FINAL

Published at https://my-dashboard-olo8.onrender.com/ . User authorized replacement on 11 November 2026. The prior publication is preserved under /legacy/ and in the local dated backup; previous commit d1f63bc0116c2313fb5047820975212789e0aa92.

Runtime workspace: C:\Ben\mt5\aurum_cluster_v2. Python: C:\Ben\mt5\.venv\Scripts\python.exe. This is a static snapshot site, refreshed on explicit request, not a continuously connected trading service. No tasks or trading operations were installed.

Manual refresh: run `C:\Ben\mt5\.venv\Scripts\python.exe C:\Ben\mt5\aurum_cluster_v2\refresh_snapshot.py`. It reads native MT5 XAUUSD.pro H1, verifies overlapping OHLC, excludes forming-candle information, reproduces all 70 archived entries/outcomes, and writes site/cluster-data.json. Inspect build_receipt.json and current broker data cutoff. Publish the reviewed generated JSON to repository root with an explicit scoped Git commit/push. The browser Reload published data button retrieves the published snapshot; it does not access MT5. Do not re-run stage_release.py for routine refreshes because it is the initial migration script.

Reference engine hash: d150b44886886b431329f4a175ad51803d3ed55287e62fdccf6b42add92ac4c9. Its signal thresholds are unchanged. The adapter extends the historical end-date boundary and processes the current known open without using its forming close/high/low. The original rules remain frozen. source/H1_indicator_ledger.csv, source/engine.py and source/outcomes.json in the runtime workspace are the preserved replay inputs. Reference copies of build.py, refresh_snapshot.py and reference_engine.py here support review; copying this directory alone does not supply the archived input data.

Solid chart paths are observed H1 closes. Historical peak markers use retrospective bar extremes. Dotted paths follow a qualified active cycle or explicitly labeled pending breakout, only after the last completed candle. Their length is one latest ATR over an illustrative visual interval, not a price/time prediction, recommended target or guaranteed continuation. Opposing open cycles or no direction produce no single projection. Snapshots older than90minutes suppress current projections. The historical target is3500points=.35hundred price units=35.00 for this symbol; outcome is MFE before the defined completed-H1 EMA10/20 turn, not realized profit. MAE may occur after a target hit.

Validation:70/70 archived entries and their MFE/MAE/turns match. Native overlap exact; forming candle excluded. Browser smoke checks on desktop/mobile:71current entry records; historical view has no projected segment; period filter; no horizontal page overflow; stale projection suppressed; no JavaScript exceptions. Legacy page link is retained.

Rollback: revert the dashboard replacement commit using an ordinary Git revert, then push main; retain historical research data. No force push or reset is required.


Multi-asset shell: assets.json is the instrument registry. Every published asset must supply its own snapshot path, exact symbol, point/digits and model version. Snapshot identity is verified before rendering. Assets without a published model show an empty state, never another instrument's prices, signals or statistics. Registry includes14 broker instruments across currencies, metals and indices. Only XAUUSD.pro currently has a published signal snapshot. Benchmarks and price precision are instrument-specific. Add approved per-asset snapshots without modifying frozen XAUUSD rules.
