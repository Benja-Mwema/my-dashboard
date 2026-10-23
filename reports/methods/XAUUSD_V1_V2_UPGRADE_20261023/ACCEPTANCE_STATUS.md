# Acceptance status

This table reports execution evidence as of 23 October 2026 EAT. Test specifications in the source instruction package are not themselves proof of execution.

## Executed checks

| Check | Input/evidence | Result | Notes |
|---|---|---|---|
| Frozen V1 identity verifier | Existing V1 freeze | EXECUTED_PASS | Snapshot integrity PASS; live-source identity MATCH; no changes/missing files. |
| Frozen V2 identity verifier | Existing V2 freeze | EXECUTED_PASS | Snapshot integrity PASS; fixed-source identity MATCH; no changes/missing files. |
| Frozen V3 identity verifier | Existing V3 freeze | EXECUTED_PASS | Receipt/snapshot PASS; source identity MATCH; no changes/missing files. |
| Accepted extractor suite | `tests/test_xauusd_extract.py` | EXECUTED_PASS | 17 passed. First attempt used a basetemp whose parent did not exist and produced setup errors; created the isolated directory and reran successfully. |
| New adapter/custody tests | `04_TESTS/test_research_adapters.py` | EXECUTED_PASS | 16 passed. Covers certificate-gated `FINAL`, event ordering, exact numeric no-chase boundaries, and incomplete/stale data; early iterations exposed and corrected a test-string mismatch, schema punctuation, and false boolean handling in required-field validation. |
| Research schemas and templates parse as JSON | `03_SCHEMAS/*.json` | EXECUTED_PASS | JSON syntax only; semantic JSON Schema validation with a third-party schema engine is not claimed. |
| Archived 17 Oct package inspection | `output/weekly_20261016/` | EXECUTED_PASS — PROVISIONAL | All four files passed row/indicator/OHLC/causal-close checks and expected close matched archived validation. Session/tick finality is not independently certified by this new adapter; status correctly remains PROVISIONAL. CLI returns nonzero for provisional status by design. Separate synthetic certificate test proves a matching session/tick certificate is required for `FINAL`. |
| Candidate root isolation | New research directory | EXECUTED_PASS | Directory created under authorized workspace; no Git repository exists at workspace root. |
| V1/V2 original cohort inventory | Original `STUDY_PROTOCOL.json` and journals | EXECUTED_PASS | Planned 20 weeks (26 Oct 2026–12 Mar 2027); zero issued forecasts, zero outcomes; files were not modified. |

## Acceptance test disposition

`EXECUTED_PASS` means the exact stated candidate check ran. `CONTRACT_ONLY` means methodology is documented or reviewed but its full source-backed behavior was not replayed. `NOT_RUN_MISSING_INPUT` means original necessary evidence/issuance artifacts were not found. Everything else remains `NOT_RUN` and must pass before any review of readiness.

| IDs | Status | Evidence / limitation |
|---|---|---|
| DATA-01 | EXECUTED_PASS | Synthetic H4/H1/M30/M15 03:45 cut verifies 00:00/03:00/03:30/03:45 expected boundaries when explicitly supplied; the output remains PROVISIONAL until session certificate exists. |
| DATA-02, DATA-03 | NOT_RUN | Weekend and shortened-session certification requires a verified instrument session source. |
| DATA-04 | EXECUTED_PASS | Synthetic future/forming close rejected by adapter test. Existing extractor test suite also passes. |
| DATA-05 | EXECUTED_PASS | Synthetic duplicate-open rejection. |
| DATA-06 | EXECUTED_PASS | Synthetic impossible OHLC rejected. |
| DATA-07, DATA-08 | EXECUTED_PASS | Synthetic package with M30/M15 stopped at 07:30 while H4/H1 reach 12:00 returns `INCOMPLETE EVIDENCE`; one H4 row versus 90 required is rejected as an incomplete window. |
| DATA-09 | EXECUTED_PASS — SYNTHETIC CERTIFICATE | With a supplied matching certificate, an inherited stale warning remains recorded while actual/expected boundary matches. This exercises preservation semantics; it is not certification of the actual broker calendar. |
| DATA-10 | NOT_RUN | Tick archive/revision interval coverage not re-executed. |
| DATA-11 | EXECUTED_PASS | Missing expected boundary is rejected rather than guessed. |
| DATA-12 | EXECUTED_PASS | Missing/nonpositive exact-time ATR and invalid geometry return `NOT_CALCULABLE`; no official trading verdict is emitted. |
| CUST-01, CUST-02 | EXECUTED_PASS | Synthetic custody test rejects retrospective backdating/late registration. |
| CUST-03, CUST-04, CUST-06 | EXECUTED_PASS — IDENTITY ONLY | Active-level hash, V1/V2/V3 verifiers, and empty original journals recorded. No files were rewritten. |
| CUST-05 | EXECUTED_PASS | Research registry exclusive-create/hash receipt tested. Timestamp is local self-attestation, not notarization. |
| CUST-07 | CONTRACT_ONLY | Example preserves V1 content; a controlled paired same-evidence Codex parity re-run was not performed. |
| CUST-08 | EXECUTED_PASS — IDENTITY ONLY | V3 freeze verifier PASS; candidate does not modify V3. |
| STR-01–STR-10 | CONTRACT_ONLY | Codex reasoning/report rules drafted; no source-backed adversarial case suite executed. |
| ROUTE-01, ROUTE-02, ROUTE-03, ROUTE-06, ROUTE-07 | EXECUTED_PASS | Synthetic facts verify target-before-origin, same-bar UNKNOWN, no-origin, failure-first, and target-then-later-failure ordering. |
| ROUTE-04, ROUTE-05, ROUTE-08, ROUTE-09, ROUTE-10 | CONTRACT_ONLY | Gap/consumed objective, completed-close-only invalidation, expiry, no-gate target contact, and new assessment after consumption remain procedure requirements without executed fixture coverage. |
| GATE-08–GATE-13 | EXECUTED_PASS | Synthetic no-chase arithmetic checks 64.999% vs 65.000%, 2.500 vs 2.499 ATR (including both failing), missing geometry/ATR, and refusal to calculate before full confirmation. Output is numeric-only, not a verdict. |
| GATE-01–GATE-07, GATE-11, GATE-14–GATE-17 | CONTRACT_ONLY | Existing gate hierarchy, coexistence timing, V3 separation, current-cutoff recheck and verdict taxonomy are preserved in the procedure but not source-backed fixture replays. |
| AUG-01–AUG-05 | NOT_RUN_MISSING_INPUT | Existing documents preserve expected cases and V2 validation explicitly says the human judgments were not historically re-executed. Original forecast + complete issued EVALUATE records were not located as a matched set. |
| DEV-01–DEV-07 | CONTRACT_ONLY | Contaminated retrospective examples are recorded in the instruction package; not re-run as independent performance evidence. |

## Required follow-up before candidate acceptance

Implement or independently source a broker/session calendar adapter; add week-end and shortened-session boundary tests; exercise tick revision coverage on a preserved source; add route/gate chronology fixtures; re-run source-backed AUG cases only where original forecast and cutoff evidence are complete; independently review the report examples; then issue a separate, pre-registered parallel-study protocol before any target week. Until then the decision remains `REVIEW_REQUIRED`.
