"""Build the WS30 dashboard feature-parity release without changing signal engines."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'ws30.html'
s=p.read_text(encoding='utf-8')
assert 'id="selectionMetrics"' not in s, 'Already upgraded; edit feature assets directly'
s=s.replace('ws30.css?v=1','ws30.css?v=features-2').replace('ws30.js?v=1','ws30.js?v=features-2')
s=s.replace('<title>AURUM | WS30.pro Frozen Rules</title>','<title>AURUM | WS30 Both Directions</title>')
s=s.replace('Four formations. One evidence record.','WS30. Four rules. Both directions.')
toolbar="""<section class="panel" aria-label="Dashboard controls"><div class="filters">
<label>Instrument<select id="instrument"><option value="WS30.pro">WS30.pro · Dow Jones</option></select></label>
<label>Evidence<select id="dataset"><option value="ws30-data.json">Latest published snapshot</option><option value="ws30-replay.json">Frozen deployment replay</option></select></label>
<label>Chart view<select id="chartMode"><option value="journey">Entry journey · AUDCAD style</option><option value="technical">Candles + EMA + MACD</option><option value="frozen">Original ATR evidence chart</option></select></label>
<label>Exit rules<select id="exitRules"><option>WS30 frozen · TP2 / SL3 / BE H1 2C</option></select></label>
<button id="reload" type="button">Reload published data</button></div>
<p id="notice" class="muted" role="status" aria-live="polite">Loading verified WS30 evidence…</p>
<p class="muted">15-minute publication and page refresh. WS30 uses ATR distances, not currency pips. Chart views preserve the same frozen outcomes.</p></section>
<section class="stats" id="selectionMetrics" aria-label="Filtered performance">
<article><span>Selected admissions</span><strong id="selectedCount">—</strong><small id="selectedSides"></small></article>
<article><span>Nonnegative closed rate</span><strong id="nonnegativeRate">—</strong><small id="selectedOutcomes"></small></article>
<article><span>Closed gross R</span><strong id="selectedGross">—</strong><small id="selectedExcluded"></small></article>
<article><span>Target-hit rate</span><strong id="selectedTarget">—</strong><small>WIN / final scored; BE and timeouts included</small></article></section>
"""
s=s.replace('<section class="stats" aria-label="WS30 research status">',toolbar+'<section class="stats" aria-label="WS30 research status">')
s=s.replace('<option value="DEVELOPMENT_2026">','<option value="DEVELOPMENT_2026" selected>')
s=s.replace('<div class="tablewrap"><table><thead><tr><th>Signal H1 close</th>', '<div class="filters"><button id="export" type="button">Export selected entries CSV</button><a id="download" href="ws30-data.json" download>Snapshot JSON</a><a href="ws30-acceptance.json">Replay acceptance</a></div><div class="tablewrap"><table><thead><tr><th>Signal H1 close</th>')
s=s.replace('<div class="controls filters">','<div class="filters"><label>Research entry<select id="selected"></select></label><button id="latest" type="button">Latest entry</button><label>Post-TP chart context<select id="postContext"><option value="48">48 H1 bars after TP</option><option value="all">Continue to latest observation</option></select></label></div><div class="controls filters">')
s=s.replace('<div id="caseFacts" class="facts"></div>','''<p id="journeyLegend" class="muted"></p><div id="caseFacts" class="facts"></div>
<details id="indicatorPanel"><summary>Confirmation-time indicator inspection</summary>
<p class="muted">Display-only indicators from completed native H1 candles: EMA10/20/50/200 and MACD12/26 with SMA9 signal. Seeded at the first published candle; these do not replace the frozen four-rule calculations or imply additional entry conditions.</p>
<div class="tablewrap"><table><thead><tr><th>Completed H1</th><th>EMA10</th><th>EMA20</th><th>EMA50</th><th>EMA200</th><th>Δ EMA10</th><th>Δ EMA20</th><th>Δ EMA50</th><th>MACD main</th><th>SMA9 signal</th></tr></thead><tbody id="features"></tbody></table></div></details>
<details><summary>Entry identity and overlapping research observations</summary><p id="overlapDetails" class="muted"></p></details>''')
s=s.replace('<footer>AURUM','<section class="panel"><h2>Journey display and WS30 exit rules</h2><p>Small dots project the entry-to-target guide without forecasting a target time. Solid green follows sampled observed prices before exit; spaced pink dots mark adverse sampled movement. At TP, the position ends and purple context may continue. BE, SL and timeout paths end at the archived exit.</p><p>A retracement marker is descriptive only: completed H1 closes retracing more than half of prior favourable completed-close movement. It does not change WS30’s frozen +2ATR target, −3ATR stop, +1ATR BE threshold, H1 two-candle protection rule or 24-H1 horizon. Actual archived BE activation is marked separately. The AUDCAD M30 retracement exit is not applied to WS30.</p><p>R uses the initial 3ATR risk. Index price units and broker points (0.1) are shown separately. C1 and Combined may share the same economic entry; totals are admission-level research sums, not a funded portfolio.</p></section><footer>AURUM')
p.write_text(s,encoding='utf-8')
j=ROOT/'ws30.js'
s=j.read_text(encoding='utf-8')
s=s[:s.rfind("\nload().catch")]
j.write_text(s+'\n'+(ROOT/'tools/ws30_features.js').read_text(encoding='utf-8'),encoding='utf-8')
with (ROOT/'ws30.css').open('a',encoding='utf-8') as f:
 f.write("""
/* AUDCAD-style controls and inspection, WS30 feature release 2. */
button{cursor:pointer;border:1px solid #73898d;background:#243438;color:#eff2ee;border-radius:7px;padding:10px 13px;font:inherit}
button:hover{border-color:#e6ca8a}button:disabled{opacity:.5;cursor:wait}
a{color:#dfc38a}select{max-width:100%}.filters{align-items:end}.filters label{min-width:0}
#selected{max-width:550px}#notice{overflow-wrap:anywhere}.filters a{padding:10px 0}
details{margin:16px 0}summary{cursor:pointer;color:#dcc38a;margin:10px 0}
#riskGraphic svg{max-width:none}#features td{font-variant-numeric:tabular-nums}
#selectedCount,#nonnegativeRate,#selectedGross,#selectedTarget{font-size:1.9rem}
@media(max-width:600px){.filters label{width:100%}.filters select,#selected{width:100%;max-width:100%}.filters button{max-width:100%}}
""")
shutil.copyfile(Path(r'C:\Ben\mt5\aurum_cluster_v2\ws30\release_v1_0\ws30-data.json'),ROOT/'ws30-replay.json')
print('WS30 feature assets prepared; original engines and snapshots unchanged.')
