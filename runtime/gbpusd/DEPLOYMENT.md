# GBPUSD on AURUM

Public route https://my-dashboard-olo8.onrender.com/gbpusd.html

Runtime C:\Ben\mt5\aurum_cluster_v2\gbpusd
Publishing checkout D:\render_sites\my-dashboard
Shared task AURUM Dashboard Refresh 15 Minutes

GBPUSD is the eighth instrument. Its page follows EURJPY's native M30 adapter and the same shared navigation, entry register, frozen replay inspection, filters, cost and horizon selectors, monthly counts, CSV/JSON/SVG exports, Formation/Journey charts, current/forming candle context, pan, zoom, hover, fullscreen and thick translucent cluster lines with price and direction.

The GBPUSD_M30_E1_V0_1 engine retains the transfer-guide E1 v0.1 rules. Source initialization starts 2 January 2025. The frozen research snapshot has 12,432 initialization bars and 10,925 completed 2026 bars through 17 November 14:30 broker-label close, 109 entries (51 BUY, 58 SELL), and 218 exact 12/24-bar outcomes. Primary gross rate 48.62%; after a hypothetical two-pip cost 42.20%. The monthly >80% objective was not met. Publication is research display, not strategy validation or broker execution.

GBPUSD point/tick size is 0.00001 and pip size 0.0001. Display prices use five decimals. Source timestamps remain native broker labels; no unverified historical UTC/EAT conversion is added. Forming candles supply current chart context and, where observable, a next-open entry proxy; they never generate completed-candle E1 signals. Frozen replays remain immutable in normal refresh.

The optional adverse 35-pip display filter is retrospective only. It is not an E1 condition or stop. Model convergence is <=0.50 current model ATR; the shared <=0.25 preceding display ATR cluster is chart context only. No SL, TP, BE, position size or order API is introduced.

Refresh verifies immutable source and engine hashes, all 109 archived signals and 218 endpoints, unique IDs, source-prefix OHLC and native overlap. Failures retain the preceding verified GBPUSD snapshot while other assets continue. GBPUSD joins the existing recoverable publisher transaction and 15-minute Windows task; no additional scheduler is created.

Backend, tests and source evidence are versioned under runtime/gbpusd. Deployment verifies the seven pre-existing instruments' data and frozen replay hashes remain untouched. Run build_snapshot.py --offline for the saved snapshot, build_snapshot.py for fresh MT5 data, test_engine.py for replay/causality tests, and test_ui.py for all eight pages. verify_public.py checks served hashes and actual browser behavior; verify_refresh.py checks a subsequent scheduler run.

Rollback only this integration change after reviewing subsequent refresh commits. Disable only the GBPUSD module if necessary. Use deployment_receipt.json and its timestamped backup; never reset the shared repository or replace the publisher from an obsolete backup. Restore the task's previous enabled state after maintenance.
