# EURJPY on AURUM

Public route https://my-dashboard-olo8.onrender.com/eurjpy.html

Runtime C:\Ben\mt5\aurum_cluster_v2\eurjpy
Publishing checkout D:\render_sites\my-dashboard
Shared task AURUM Dashboard Refresh 15 Minutes

EURJPY is the seventh published instrument, alongside Gold, GBPJPY, AUDCAD, WS30, DAX40 and CADJPY. The implementation follows CADJPY's data adapter and the shared chart/workspace/navigation components, with a native M30 duration of 1,800 seconds. The existing six instruments retain their own rules and H1 chart duration. Rule identity EURJPY_M30_E1_V0_1 is the unchanged transfer-guide E1 v0.1 research baseline. This deployment does not promote the rule to a validated strategy or enable broker orders.

The frozen replay is the 17 November 2026 research snapshot: 12,432 prior 2025 candles and 10,923 completed 2026 candles, ending at the native 13:30 close label. Every update verifies the immutable source, engine hash, 119 archived signals (62 BUY, 57 SELL) and 238 complete 12/24-bar outcomes. The exact first-hit +2 ATR versus -1 ATR diagnostics also match the analysis. Signals and outcomes use completed candles; the current bar supplies only an already-observable next-open proxy and separate chart context. The primary default is 12 M30 candles, with 24 available as a secondary horizon. The greater-than-80% monthly objective was not achieved: 55.46% gross and 49.58% after a hypothetical 2-pip cost at 12 bars.

Features inherited from the shared dashboard: seven-instrument navigation and selector; latest/frozen datasets and Inspect frozen entries; BUY/SELL, date/year/month, phase, outcome and search filters; 12/24-bar horizons and cost scenarios; entry register, previous/next/latest entry, source JSON and filtered CSV downloads; formation and journey charts with EMA10/20/50, current/forming bar, pan/zoom/hover/fullscreen and SVG download; thick translucent solid cluster lines with prices and directions; per-entry exact predicates and monthly results. The optional 35-pip adverse filter matches CADJPY's display feature and is explicitly retrospective. It changes displayed subsets only and is neither an entry gate nor a protective stop. Default is all signals.

Model convergence is <=0.50 current ATR and uses the tested recursive seeds. The shared display cluster is <=0.25 prior display ATR; this is chart context only. No TP, SL, BE or live orders are introduced. Native time labels are retained; historical conversion to UTC/EAT remains unverified. First-seen UTC is an audit timestamp; refreshed records are still historical reconstructions.

The enabled module joins the existing recoverable publication transaction. Its failure logs an error and retains the previous EURJPY snapshot while the other assets continue. Cache prefixes and incoming native overlaps must match immutable OHLC; volume revisions are logged. Shared chart context now uses a per-instrument period and includes EURJPY M30. Frozen replay is never rewritten by normal refresh. Backend code, reference data and integration source are versioned under runtime/eurjpy in the publishing repository.

Reproduce frozen data with python build_snapshot.py --offline; refresh using python build_snapshot.py. Run python test_engine.py and python test_ui.py for engine and staged seven-page checks. Public verification checks deployed source hashes, all seven pages and live M30 chart context.

Rollback by disabling only EURJPY in config if required; preserve its source and replay. The deployment receipt and exact pre-change backup identify touched files. Revert only the integration commit after considering later publication commits, never reset the repository or replace the whole shared publisher with an obsolete file. Restore the refresh task to its original enabled state following maintenance.
