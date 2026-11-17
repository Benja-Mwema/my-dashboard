from pathlib import Path
import json,hashlib,urllib.request,time,sys,subprocess,datetime
R=Path(__file__).resolve().parent;BASE='https://my-dashboard-olo8.onrender.com/'
def get(name):
 req=urllib.request.Request(BASE+name+'?eurusd_release='+str(time.time_ns()),headers={'Cache-Control':'no-cache'})
 return urllib.request.urlopen(req,timeout=60).read()
def public():
 receipt=json.loads((R/'deployment_receipt.json').read_text());expected=receipt['files'];last=None
 for attempt in range(25):
  try:
   names=['eurusd.html','eurusd.js','aurum-ui-v1.js','aurum-workspace-v2.js','aurum-charts-v3.js','assets.json','eurusd-rules.json','eurusd-replay.json']
   for n in names:assert hashlib.sha256(get(n)).hexdigest()==expected[n],'Public bytes not updated: '+n
   data=json.loads(get('eurusd-data.json'));assert data['version']=='EURUSD_M30_E2S_V0_2' and data['validation']['archived_outcomes_exact']==156
   assert data['meta']['broker_orders_enabled'] is False
   result=dict(public_static_hashes_match=True,release_commit=receipt['commit'],symbol=data['symbol'],signals=len(data['entries']),health=data['health'],at=datetime.datetime.now(datetime.timezone.utc).isoformat())
   (R/'public_release.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True);return
  except Exception as e:
   last=str(e);print('Public release pending: '+last,flush=True);time.sleep(20)
 raise RuntimeError(last)
def refresh():
 start=datetime.datetime.now(datetime.timezone.utc);task='AURUM Dashboard Refresh 15 Minutes'
 subprocess.run(['powershell.exe','-NoProfile','-Command',"Start-ScheduledTask -TaskName '"+task+"'"],check=True)
 for attempt in range(90):
  p=R.parent/'refresh_publish_status.json'
  status=json.loads(p.read_text()) if p.exists() else {}
  stamp=status.get('completed_at',status.get('at',''))
  if stamp:
   dt=datetime.datetime.fromisoformat(stamp)
   if dt.tzinfo is None:dt=dt.astimezone()
   if dt>=start and status.get('status')=='failed':raise RuntimeError(status)
   if dt>=start and status.get('EURUSD_asof'):
    assert status['status']=='published' and len(status['chart_context_states'])==9
    data=json.loads((R/'site/eurusd-data.json').read_text());assert datetime.datetime.fromisoformat(data['generated_at'])>=start
    assert data['validation']['archived_outcomes_exact']==156
    assert not (R/'publication_warning.json').exists()
    taskinfo=subprocess.run(['powershell.exe','-NoProfile','-Command',"$t=Get-ScheduledTask -TaskName '"+task+"'; $i=$t|Get-ScheduledTaskInfo; @{Enabled=$t.Settings.Enabled;State=[string]$t.State;LastTaskResult=$i.LastTaskResult;LastRunTime=[string]$i.LastRunTime;NextRunTime=[string]$i.NextRunTime}|ConvertTo-Json -Compress"],capture_output=True,text=True,check=True)
    info=json.loads(taskinfo.stdout);assert info['Enabled']
    result=dict(status='PASS',publisher=status,task=info,eurusd_health=data['health'])
    (R/'refresh_acceptance.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True);return
  if attempt%3==0:print('Waiting for nine-instrument scheduled publisher',flush=True)
  time.sleep(10)
 raise RuntimeError('Scheduled publisher did not complete in 15 minutes')
if __name__=='__main__':refresh() if '--refresh' in sys.argv else public()
