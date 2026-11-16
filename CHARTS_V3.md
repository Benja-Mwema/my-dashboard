# AURUM shared charts v3

Presentation release for Gold, GBPJPY, AUDCAD, WS30 and DAX40, 16 November 2026.

## Behaviour

- Default: latest confirmed entry within the page's active filters.
- Formation and observed-journey views; original instrument-specific view retained.
- Consistent EMA10 gold, EMA20 blue, EMA50 purple; layer toggles.
- Display-only EMA10/20/50 cluster: width <= 0.25 preceding Wilder ATR14. Fixed detection-candle high/low; first subsequent completed close outside ends the box. Detection is never backdated.
- Gold's archived cluster remains separately outlined, retaining its original EMA trio and boundaries.
- Shared context ranges, zoom, pan, reset, hover/tap/keyboard candle inspection, chart export, lifecycle markers and post-exit fading.
- SL/TP originate only from selected rule records. Gold has a movement benchmark (not a TP); GBPJPY has an EMA-touch evaluation exit and no invented barriers. BE begins at recorded activation, never at entry.
- Numerical entry explanations use published data. GBPJPY checks the exact frozen zero-tolerance crossover/continuation rule; AUDCAD checks EMA/MACD conditions; DAX40 displays archived predicates. Missing Gold stages and WS30 stage values are explicitly unverified, never inferred passes.

## Evidence boundaries

Data and model files are not modified. Chart code writes only DOM/local display state. Missing display EMAs use recursive close EMA with 250 observations of warm-up. Published EMAs are retained. Display ATR is not substituted for the frozen trade ATR.

Broker-to-UTC history is not verified for Gold, GBPJPY, AUDCAD and WS30. These retain explicitly labelled broker clocks. DAX40 retains its existing EAT rendering. Do not invent historical offset conversion.

Selected snapshot type is independent of signal origin: a latest snapshot may contain historical replay records. Unknown intrabar exit timing is labelled as an interval/reference. H1 chart paths do not establish M1 barrier ordering.

## Files and maintenance

- aurum-charts-v3.js and .css contain the shared chart implementation.
- aurum-workspace-v2.js exposes read-only data/selection adapters plus existing selection actions.
- chart-rule-evidence-v3.json contains WS30 frozen entry definitions; displayed text excludes outcome sections.
- Five HTML files load the shared chart assets.
- Existing native chart scripts and the 15-minute publisher remain unchanged.

## Validation

Five-page browser acceptance covers selection, three EMA layers, allowed/absent barriers, zoom/pan/reset, preserved selections across views, candle keyboard inspection, SVG downloads, source JSON immutability, frozen snapshots, entry-condition audit and BE markers. Indicator calculations pass prefix invariance. Mobile width is checked at 390px; desktop/mobile screenshots are retained with the deployment checkpoint.

Local checkpoint: C:\\Ben\\mt5\\aurum_cluster_v2\\chart_v3
Rollback: restore the release's explicit file list to its recorded previous Git commit; preserve later snapshot refresh commits.
