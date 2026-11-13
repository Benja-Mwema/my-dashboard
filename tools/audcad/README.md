# AUDCAD H1 BUY/SELL frozen dashboard module

Entry IDs: AUDCAD_H1_BUY_V1_0 and AUDCAD_H1_SELL_V1_0. Independent opportunities; no orders. Authoritative specifications and original fixtures are in source/. Original file bytes and checksums are preserved. Replay cutoff 2026-11-12 22:00 broker time; M30 pairs form H1. MACD uses SMA9 signal.

Runtime C:\Ben\mt5\aurum_cluster_v2\audcad. refresh_audcad.py checks broker symbol/scale/server, historical overlap and source revisions; extends an immutable warm-up with persisted completed native_tail.json. Indicators recompute from that complete history, never a chart slice. signals.sqlite preserves unique signal IDs, first detection times, state and revision records. Last EMA values and rolling MACD main values are also checkpointed. Any source correction blocks publication and writes data_quality.json; do not silently overwrite history. Old signals discovered at initial deployment/reconnect are explicitly historical/late, not new fills.

Tests: python -m unittest discover -s . -p "test_*.py". Golden fixtures reproduce all 119 executable entries and one additional unscored signal, reference prices, barriers, outcomes, exit bars and highest pips. BUY: 30 TP, 27 SL, 1 open; SELL: 29 TP, 29 SL, 3 open, 1 unscored. Both have 47 moved >20 cases. No BE stop is introduced. Highest pips retains the archived exit-bar limitation.

The existing Windows task AURUM Dashboard Refresh 15 Minutes invokes the shared runtime refresh_publish.py. All three instrument snapshots are validated and serialized before publication in one Git commit. Interrupted publication has a recovery journal and byte-hash guards; unrelated changes stop recovery rather than being overwritten. Deployment remains static and may lag the scheduled collection by Render propagation time.

Feature flag: runtime config.json enabled=false disables AUDCAD evaluation in the shared job, which publishes audcad-config.json=false so the page stops displaying the module. To roll back immediately, publish audcad-config.json=false and disable runtime evaluation; retain signals.sqlite, native_tail.json, source and prior ledgers. Re-enabling resumes from retained records. Never edit BUY/SELL predicates or original fixture bytes as a rollback.

Dashboard audcad.html defaults to latest observation, with immutable replay as another option. Each side is separate by default. The selected entry chart shows its own TP/SL, not basket levels. Monthly CSV uses entry month. TP/SL are nominal OHLC research outcomes, not actual executions; source gaps beyond barriers are flagged. OPEN/AMBIGUOUS/UNSCORED/DATA_PENDING are excluded from resolved TP rate.

The active shared job requires the laptop awake, signed in and MT5/network available. Logs: C:\Ben\mt5\aurum_cluster_v2\refresh_publish.log and refresh_publish_status.json. No separate AUDCAD schedule was installed.
