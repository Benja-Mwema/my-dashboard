# AURUM automatic refresh

Windows task: AURUM Dashboard Refresh 15 Minutes. Runs on the MT5 laptop every 15 minutes under the signed-in user. Requires laptop awake, user signed in, MT5 and network available. Missed runs start when available; overlapping runs are ignored; each run has a ten-minute limit.

Runtime: C:\Ben\mt5\aurum_cluster_v2\refresh_publish.py

Refreshes XAUUSD from MT5 and takes the latest GBPJPY observer snapshot (or performs a fresh read when the observer snapshot is old). Validates identity, frozen XAU reproduction, GBPJPY deduplication and completed-candle timing. Publishes only cluster-data.json and gbpjpy-data.json through the established Git/Render pipeline. Frozen replay and entry rules are unchanged. Fails if the repository has uncommitted work or cannot fast-forward, leaving user work intact. Never submits orders.

Open pages reload published data every 15 minutes. Render deployment adds propagation delay; this is not streaming. Logs and last-run status are refresh_publish.log and refresh_publish_status.json in the runtime folder. Windows Task Scheduler also records LastTaskResult. Disable the named task to pause automatic publication.
