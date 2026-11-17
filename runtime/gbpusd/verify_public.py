from pathlib import Path
import urllib.request,json,hashlib,time,subprocess,sys
P=Path(__file__).resolve().parent;BASE='https://my-dashboard-olo8.onrender.com/'
receipt=json.loads((P/'deployment_receipt.json').read_text());names=['gbpusd.html','gbpusd.js','aurum-ui-v1.js','aurum-workspace-v2.js','aurum-charts-v3.js','gbpusd-replay.json']
for attempt in range(50):
 try:
  hashes={}
  for n in names:
   b=urllib.request.urlopen(BASE+n+'?verify='+str(time.time()),timeout=30).read();hashes[n]=hashlib.sha256(b).hexdigest()
  if all(hashes[n]==receipt['files'][n] for n in names):break
 except Exception:pass
 if attempt%3==0:print('Waiting for public rollout',attempt,flush=True)
 time.sleep(10)
else:raise RuntimeError('Public release hashes did not converge')
print('Public release hashes match',flush=True)
r=subprocess.run([sys.executable,str(P/'test_ui.py'),BASE],capture_output=True,text=True,timeout=240)
print(r.stdout);print(r.stderr[-2000:]);assert r.returncode==0
with urllib.request.urlopen(BASE+'market-context.json?verify='+str(time.time()),timeout=30) as r:ctx=json.load(r)
assert ctx['assets']['gbpusd']['state']=='VERIFIED_NATIVE_CONTEXT',ctx['assets'].get('cadjpy')
with urllib.request.urlopen(BASE+'gbpusd-data.json?verify='+str(time.time()),timeout=30) as r:d=json.load(r)
assert d['validation']['archived_signals_exact']==109 and d['meta']['broker_orders_enabled'] is False
assert ctx['assets']['gbpusd']['timeframe']=='M30' and ctx['assets']['gbpusd']['period_seconds']==1800
assert len(ctx['assets'])==8 and all(x['state']=='VERIFIED_NATIVE_CONTEXT' for x in ctx['assets'].values())
assert d['validation']['archived_outcomes_exact']==218 and d['meta']['timeframe']=='M30'
proof=dict(public_release_hashes=hashes,chart_context=ctx['assets']['gbpusd'],validation=d['validation'],latest_completed_m30=d['latest_completed_m30'],public_ui_all_eight_passed=True)
(P/'public_verification.json').write_text(json.dumps(proof,indent=2));print(json.dumps({k:v for k,v in proof.items() if k!='chart_context'}),flush=True)
