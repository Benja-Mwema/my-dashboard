from pathlib import Path
import json,hashlib,urllib.request,time,datetime,subprocess
P=Path(__file__).parent;APP=P.parent;R=Path(r'D:\render_sites\my-dashboard');BASE='https://my-dashboard-olo8.onrender.com/'
s=json.loads((APP/'refresh_publish_status.json').read_text());receipt=json.loads((P/'deployment_receipt.json').read_text())
assert s['status']=='published' and 'GBPUSD_asof' in s
assert datetime.datetime.fromisoformat(s['completed_at'])>datetime.datetime.fromisoformat(receipt['at'])
names=['gbpusd-data.json','market-context.json'];expected={n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in names}
for attempt in range(30):
 try:
  actual={n:hashlib.sha256(urllib.request.urlopen(BASE+n+'?refreshverify='+str(time.time()),timeout=30).read()).hexdigest() for n in names}
  if actual==expected:break
 except Exception as e:print(type(e).__name__,flush=True)
 if attempt%3==0:print('Waiting for refreshed data publication',attempt,flush=True)
 time.sleep(10)
else:raise RuntimeError('Updated snapshot has not reached public site')
frozen=[n for n in receipt['previous_data_hashes'] if 'replay' in n or 'saved' in n]
assert all(hashlib.sha256((R/n).read_bytes()).hexdigest()==receipt['previous_data_hashes'][n] for n in frozen)
assert hashlib.sha256((R/'gbpusd-replay.json').read_bytes()).hexdigest()==receipt['files']['gbpusd-replay.json']
assert not (P/'publication_warning.json').exists()
c=json.loads((R/'market-context.json').read_text());e=c['assets']['gbpusd'];assert e['forming']['time']==e['tick_native']//1800*1800 and e['period_seconds']==1800
r=subprocess.run(['powershell.exe','-NoProfile','-Command',"$t=Get-ScheduledTask -TaskName 'AURUM Dashboard Refresh 15 Minutes'; $i=Get-ScheduledTaskInfo -TaskName $t.TaskName; @{enabled=$t.Settings.Enabled;state=$t.State.ToString();last_result=$i.LastTaskResult;next=$i.NextRunTime.ToString('o')} | ConvertTo-Json -Compress"],capture_output=True,text=True,check=True)
task=json.loads(r.stdout);assert task['enabled'] is True and task['last_result']==0,task
proof=dict(refresh=s,public_updated_hashes=actual,frozen_replays_preserved=True,gbpusd_forming_label=e['forming_open_label'],gbpusd_tick=e['tick_label'],task=task,verified_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
(P/'refresh_verification.json').write_text(json.dumps(proof,indent=2));print(json.dumps(proof),flush=True)
