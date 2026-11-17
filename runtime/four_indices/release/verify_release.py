from pathlib import Path
import json,urllib.request,hashlib,time,sys,datetime,concurrent.futures
ROOT=Path(__file__).resolve().parent;BASE='https://my-dashboard-olo8.onrender.com/'
def fetch(name):
 with urllib.request.urlopen(BASE+name+'?release_check='+str(time.time_ns()),timeout=45) as response:
  assert response.status==200
  return response.read()
def main():
 receipt=json.loads((ROOT/'deployment_receipt.json').read_text())
 for attempt in range(25):
  try:
   marker=json.loads(fetch('four-indices-release.json'))
   assert marker['release']=='AURUM_FOUR_INDICES_20261117_1'
   break
  except Exception as e:
   print('Waiting for public release:',str(e)[:150],flush=True);time.sleep(15)
 else:raise RuntimeError('New public release not visible within verification window')
 required=['four-indices-release.json','assets.json','aurum-ui-v1.js','aurum-ui-v1.css','aurum-workspace-v2.js','aurum-charts-v3.js','index-candidates.js','index-candidates.css']
 for stem in ['nas100','cac40','jpn225','aus200']:required.extend([stem+'.html',stem+'-replay.json',stem+'-rules.json'])
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:results=dict(zip(required,pool.map(fetch,required)))
 for name,content in results.items():assert hashlib.sha256(content).hexdigest()==receipt['files'][name],'Public content hash differs: '+name
 snapshots={}
 for stem,count in [('nas100',7),('cac40',8),('jpn225',8),('aus200',12)]:
  d=json.loads(fetch(stem+'-data.json'));assert d['validation']['archived_outcomes_exact']==count*2
  assert d['meta']['model_hash']==marker['model_hash'] and d['meta']['broker_orders_enabled'] is False
  assert all(p['passed'] is not False for e in d['entries'] for p in e['predicates'])
  snapshots[stem]=dict(entries=len(d['entries']),archived_outcomes_exact=count*2,health=d['health'],generated_at=d['generated_at'])
 result=dict(status='PUBLIC_CONTENT_VERIFIED',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),deployment_commit=receipt['commit'],static_files_exact=len(required),marker=marker,snapshots=snapshots)
 (ROOT/'public_content_verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
 from test_ui import main as ui
 ui(BASE)
if __name__=='__main__':main()
