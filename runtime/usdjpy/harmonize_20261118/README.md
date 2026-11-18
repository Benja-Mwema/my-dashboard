# USDJPY shared chart harmonization — 18 November 2026

USDJPY uses the same AURUM Monitor, Research and Audit workspace and interactive chart as the other deployed instruments. Pan, zoom, EMA layers, cluster overlays, candle inspection, entry evidence, SVG export and frozen replay are shared components.

This release changes presentation only. H1 E1 v0.2 remains a frozen research baseline, with performance not evaluated. Published OHLC, EMA10/20/50, ATR14 and depth values are retained exactly. Additional chart context continues the frozen indicator recurrence. Convergence uses 0.50 current ATR; directional markers require an existing published E1 confirmation. Forming bars cannot confirm a cluster or signal.

No formula, configuration, market dataset, signal, registry, email setting or order code is changed. The deployer guards prior presentation hashes, preserves all root JSON and rule documents and verifies the frozen manifest and files. Runtime site copies are kept consistent. Existing page script URLs are cache-busted.

`test_ui.py` checks desktop and mobile interactions, exact indicator parity, immutable source data, all 55 frozen formations and 14 other instrument routes. With a base URL argument it tests the public deployment. Without an argument it serves the staging preview. `ui_acceptance.json` records the preview pass. Operational deployment and public verification receipts remain in the workstation staging folder.
