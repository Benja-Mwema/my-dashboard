# AURUM four-index candidate release — 17 November 2026

Public origin: https://my-dashboard-olo8.onrender.com/

| Page | Detector | Saved entries |
|---|---|---:|
| nas100.html | D04_A1, zone 0.25, EARLIER after full family selection | 7 |
| cac40.html | H01_BASE, BUY and SELL, original reservations | 8 |
| jpn225.html | Combined_BASE, F1W4 after original family priorities | 8 |
| aus200.html | D04_BASE, ORIGINAL and EARLIER, SELL | 12 |

These are research candidates selected from the 2026 work. They have not passed independent validation. JPN225 recurrence is concentrated in January–June. This release does not promote them to validated production strategies and does not place orders.

Navigation order: Metals (Gold), Indices (WS30, DAX40, NAS100, CAC40, JPN225, AUS200), Currencies (EURUSD, GBPUSD, EURJPY, GBPJPY, CADJPY, AUDCAD). Existing instrument models and archived records remain unchanged.

## Runtime and publication

- Repository: `D:\render_sites\my-dashboard`, branch `main`; existing Render Git deployment.
- Builders: `C:\Ben\mt5\aurum_cluster_v2\four_indices`.
- Source archive: `C:\Ben\mt5\research_four_indices_ws30_20261117_v01`.
- Existing task: `AURUM Dashboard Refresh 15 Minutes`; `refresh_publish.py` publishes native chart context first, then the validated instrument snapshots.
- Four new detectors join that task with per-instrument failure isolation. Failed updates retain the last verified snapshot. Candidate errors appear in `four_indices/*_publication_warning.json` and the common publication log.
- Cache stores immutable original bars plus newly confirmed native bars. An OHLC revision or missing M1/H1/M15 price aggregation stops that instrument's update. Volume revisions are counted; they do not alter these price-only rules.
- Native chart context and forming candles are separate from signal inputs. Historical native broker labels are not relabelled as EAT. Publication times use EAT in the interface.
- Both saved research and current observations expose charts, entry inspection, formula evidence, ATR targets, period filters, CSV, selected-record JSON and SVG downloads.

## Contract and checks

First eligible confirmed native M15 opening after H1 confirmation is the entry reference. Stop is −3 fixed ATR; +2 ATR is primary and +3 ATR is a comparison. Two eligible H1 closes at least +1 ATR schedule guarded BE at the next eligible M1 opening. H01 uses pre-breach ATR; the other candidates use signal ATR. Full 24-native-H1 horizon is required for final scoring. Ambiguous and censored records remain unscored. Net research R includes recorded-spread proxy and adverse gaps; it is not portfolio or bid/ask execution P/L.

Every refresh reproduces the 35 archived entries and 70 outcome profiles, including prices, ATR, exit timing and net R. Causal prefix checks use April, July and October cutoffs for all four candidates. Native M1 price aggregation is checked against M15 and H1. See `release/engine_acceptance.json` and `release/ui_acceptance.json` for release evidence. Saved replay is immutable; post-research observations are separately labelled with first-seen times.

## Recovery

The installer pauses the common task only during publication and restores its prior enabled setting in `finally`. It waits for an active refresh, requires a clean checkout and expected shared-file hashes, backs up modified files, and checks all existing instrument datasets remain byte-identical. If pre-commit work fails, only its own unchanged writes are rolled back. A successful push is recorded in `four_indices_release_20261117/deployment_receipt.json` with backup paths and commit IDs. Do not restore old snapshot files over newer scheduled publication; revert the specific code commit and matched runtime integration deliberately if necessary.

Provider data revisions can make other pre-existing instruments unavailable independently of this release. Do not bypass their data gates to make freshness indicators appear green.
