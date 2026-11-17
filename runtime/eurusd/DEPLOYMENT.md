# EURUSD AURUM deployment — 17 November 2026

Public route: https://my-dashboard-olo8.onrender.com/eurusd.html

Backend: C:\Ben\mt5\aurum_cluster_v2\eurusd
Site checkout: D:\render_sites\my-dashboard
Scheduler: AURUM Dashboard Refresh 15 Minutes
Git archive: runtime/eurusd

SELL-only M30 E2-S v0.2 / F162. Research candidate; later consistency gate failed. No broker orders or changes to other models. Baseline archive has 53 signals, 52 entered observations and one cancelled next-open gap. All 156 endpoints across 6/12/24 bars match the research ledger. Default chart view shows current context, default metric uses 12 bars and hypothetical two-pip round-trip cost. Original rules and source remain immutable via SHA256 gates. Costs do not simulate fills or portfolio returns.

The new module verifies its archived source prefix against MT5 overlap, never overwrites historical OHLC, and excludes the actual last native bar from confirmed research calculations even if the feed is lagging. Current chart context is separate and can include a provisional forming bar. Native timestamps are not relabelled as UTC/EAT. Source lag and publication age are displayed independently.

Initial release: run test_engine.py, build_snapshot.py, prepare_preview.py, test_ui.py, then deploy.py. Deployment disables the shared task briefly, waits for an existing run, verifies shared source hashes, backs up all modified targets, preserves existing data files, commits/pushes explicit paths, and restores the task. Before commit, failures restore only files still equal to this release's writes. After commit, never reset another publisher's work; use a reviewed revert if required. Deployment receipt records preceding commit and backup manifest.

Every scheduled refresh runs the EURUSD builder with frozen parity checks. EURUSD failure retains its last verified data and leaves other modules running; publication_warning.json records the error and publication age exposes stale snapshots. Frozen replay is never refreshed. New signals retain first-seen UTC and their original broker labels. Continue to show failed later-validation status until separately authorized research produces a replacement.

Acceptance: exact research parity; eleven causal monthly prefixes; pending next-open and cancellation; all nine routes, timeframe/bar durations, shared navigation, mobile overflow and JavaScript errors; EURUSD filtering, horizons, costs, cancelled record, conditions, EMA200, CSV/JSON/SVG downloads; existing GBPUSD/EURJPY/CADJPY replay checks. Public verification and a complete shared publisher cycle follow deployment.
