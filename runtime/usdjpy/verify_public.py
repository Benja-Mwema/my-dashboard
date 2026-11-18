from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,time,urllib.request
P=Path(__file__).resolve().parent;BASE='https://my-dashboard-olo8.onrender.com/'
def get(name):
 req=urllib.request.Request(BASE+name+'?verify='+str(time.time_ns()),headers={'Cache-Control':'no-cache','User-Agent':'AURUM-release-verification'})
 with urllib.request.urlopen(req,timeout=45) as r:return r.read()
def sha(b):return hashlib.sha256(b).hexdigest()
receipt=json.loads((P/'deployment_receipt.json').read_text())
for attempt in range(60):
 try:
  checked={}
  for n in ['usdjpy.html','usdjpy.js','usdjpy.css','usdjpy-replay.json','usdjpy-rules.json']:
   checked[n]=sha(get(n));assert checked[n]==receipt['public_files'][n],n+' not yet at intended release'
  a=json.loads(get('assets.json'));u=next(a for a in a['assets'] if a['symbol']=='USDJPY.pro')
  assert u['module_page']=='usdjpy.html' and u['status']=='published' and u['model_version']=='USDJPY_H1_E1_v0.2'
  d=json.loads(get('usdjpy-data.json'));assert d['meta']['frozen'] is True and d['meta']['broker_orders_enabled'] is False
  assert d['version']=='USDJPY_H1_E1_v0.2' and d['meta']['timeframe']=='H1' and d['meta']['ema_periods']==[10,20,50]
  assert len(d['entries'])>=55 and d['validation']['baseline_formations_exact']==55
  assert d['health']['state']=='OK' and (datetime.now(timezone.utc)-datetime.fromisoformat(d['generated_at'])).total_seconds()<2100
  assert all(e['signal_available_at']<=d['latest_completed_h1'] for e in d['entries'])
  ctx=json.loads(get('market-context.json'))['assets']['usdjpy'];assert ctx['state']=='VERIFIED_NATIVE_CONTEXT' and ctx['timeframe']=='H1'
  result={'status':'PUBLIC_CONTENT_VERIFIED','checked_at_utc':datetime.now(timezone.utc).isoformat(),'commit':receipt['commit'],
   'url':BASE+'usdjpy.html','static_hashes_exact':checked,'registry_verified':True,'frozen':True,'performance_status':d['meta']['performance_status'],
   'formations':len(d['entries']),'latest_completed_h1':d['latest_completed_h1'],'health':d['health'],'chart_context_native_tick':ctx['tick_label']}
  (P/'public_verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True);break
 except Exception as e:
  if attempt%2==0:print('Waiting for published release: '+str(e),flush=True)
  if attempt==59:raise
  time.sleep(15)
