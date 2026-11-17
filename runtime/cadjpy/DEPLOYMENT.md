# CADJPY on AURUM — H1 E1 v0.1

Public route: https://my-dashboard-olo8.onrender.com/cadjpy.html

Runtime: C:\Ben\mt5\aurum_cluster_v2\cadjpy
Publishing checkout: D:\render_sites\my-dashboard
Shared task: AURUM Dashboard Refresh 15 Minutes

Entry logic is the tested E1 guide adaptation to H1: BUY persistence 2–8 and SELL 4–16, depth ≤0.50 ATR, directional strict EMA ordering, slope signs, price-unit expansion, candle direction/location, price progression and SELL lower-pair gate. One signal per episode across both directions. No execution API. The research model has no protective SL, TP, BE, or retracement exit. A 35-pip adverse filter is retrospective.

The immutable source spans January 2024 through 16 November 2026, including indicator/episode warm-up. Its 49 scored 2026 signals (28 BUY, 21 SELL) and 98 fixed-horizon outcomes must reproduce exactly on every refresh. Frozen hashes cover source, expected signals and engine. The frozen replay JSON remains unchanged during refresh; current data appends verified native H1 bars to a local cache. OHLC revisions fail closed and retain the previous published snapshot. Tick-volume revisions are logged and do not alter this OHLC-only rule. The forming next-open proxy may establish an entry but forming highs/lows/closes never enter features or outcomes.

Use `python build_snapshot.py --offline` only to reproduce the frozen initial replay; routine updates run `python build_snapshot.py`. `python test_engine.py` validates prefix causality, pending outcomes and gap cancellation. `python test_ui.py` exercises the staging preview; pass the public base URL for live checks. The existing shared publisher calls the builder and includes cadjpy-data.json in its recoverable transaction. CADJPY failure retains its previous verified dataset and does not block other assets. The chart context builder includes CADJPY in its fast current/forming-bar snapshot; it does not feed the research model.

Features: shared six-asset navigation and selector; latest/frozen datasets; BUY/SELL, month/year, outcome/search, phase, cost and adverse filters; 12/24-bar endpoints; first-seen audit; signal inspection and exact feature evidence; current and historical candles/EMAs; forming bars clearly separated; pan/zoom/hover, lifecycle markers, previous/next/latest navigation, SVG/JSON/CSV exports; monthly summaries; phase recurrence; responsive layout and freshness status. Shared chart display clusters (0.25 prior ATR) are explicitly separate from E1 model convergence (0.50 current ATR); exact model predicates are in Why this entry.

All records are labelled historical reconstructions, including later refreshes. First-seen time is an audit timestamp, not a claim of prospective performance. Only complete outcomes enter rates; positive is strictly greater than zero and flats stay in denominator. Two-pip costs are hypothetical. No portfolio drawdown or executed-trade performance is implied by overlapping signals. Broker timestamps retain native labels, not unverified EAT conversion. Source freshness and publication freshness are separate.

Rollback: disable CADJPY via its runtime config if needed. A CADJPY release receipt captures the previous commit and backups. Revert the specific integration commit only after checking subsequent publication changes; never reset the repository or replace the whole publisher with an old copy. Preserve other instruments and appended history. Restore the shared task to its original enabled state after any maintenance. Backend source and reference data are versioned under runtime/cadjpy in the publication repository; active Windows runtime remains the location above.
