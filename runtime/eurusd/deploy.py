from pathlib import Path
import subprocess,json,hashlib,time,shutil,sys,datetime
ROOT=Path(__file__).resolve().parent;APP=ROOT.parent;REPO=Path(r'D:\render_sites\my-dashboard');TASK='AURUM Dashboard Refresh 15 Minutes'
def run(a):
 r=subprocess.run(a,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=240)
 if r.returncode:raise RuntimeError(r.stderr[-3000:]+r.stdout[-3000:])
 return r.stdout.strip()
def ps(s):return run(['powershell.exe','-NoProfile','-Command',s])
def git(*a):return run(['git','-C',str(REPO),*a])
def digest(b):return hashlib.sha256(b).hexdigest()
def main():
 assert len(json.loads((ROOT/'ui_acceptance.json').read_text()))==9,'All nine UI routes must pass'
 assert json.loads((ROOT/'engine_acceptance.json').read_text())['horizon_outcomes_exact']==156
 was_enabled=ps("(Get-ScheduledTask -TaskName '"+TASK+"').Settings.Enabled").lower()=='true'
 ps("Disable-ScheduledTask -TaskName '"+TASK+"' | Out-Null")
 backup=ROOT/('deployment_backup_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir(exist_ok=False);modified={};previous=None;committed=False
 try:
  for j in range(90):
   running=ps("$svc=New-Object -ComObject Schedule.Service; $svc.Connect(); @($svc.GetRunningTasks(0) | Where-Object { $_.Name -eq '"+TASK+"' }).Count")
   if running=='0':break
   if j%3==0:print('Waiting for existing scheduled refresh to finish',flush=True)
   time.sleep(10)
  else:raise RuntimeError('Existing refresh did not finish; no deployment changes made')
  assert not (APP/'publish_transaction.json').exists(),'Publisher transaction unfinished'
  assert not git('status','--porcelain'),'Unrelated checkout changes preserved'
  assert git('branch','--show-current')=='main'
  git('fetch','origin','main');git('merge','--ff-only','origin/main');previous=git('rev-parse','HEAD')
  for n,h in json.loads((ROOT/'expected_shared.json').read_text()).items():
   p=REPO/n[5:] if n.startswith('site/') else APP/n[8:]
   assert digest(p.read_bytes())==h,'Shared file changed since inspection: '+n
  unaffected=['cluster-data.json','cluster-saved.json','gbpjpy-data.json','gbpjpy-replay.json','audcad-data.json','audcad-replay.json','ws30-data.json','ws30-replay.json','dax40-data.json','dax40-replay.json','cadjpy-data.json','cadjpy-replay.json','eurjpy-data.json','eurjpy-replay.json','gbpusd-data.json','gbpusd-replay.json']
  preserved={n:digest((REPO/n).read_bytes()) for n in unaffected}
  target={REPO/f.name:f.read_bytes() for f in (ROOT/'site').iterdir() if f.is_file()}
  names=['engine.py','build_snapshot.py','config.json','test_engine.py','test_ui.py','DEPLOYMENT.md','deploy.py','reference/source.csv','reference/signals.csv','reference/rule.json','engine_acceptance.json','ui_expected.json','ui_acceptance.json','expected_shared.json','prepare_preview.py','verify_release.py']
  for n in names:target[REPO/'runtime/eurusd'/n]=(ROOT/n).read_bytes()
  for n in ['refresh_publish.py','build_market_context.py']:
   b=(ROOT/'integration'/n).read_bytes();compile(b.decode(),n,'exec');target[APP/n]=b;target[REPO/'runtime/eurusd/integration'/n]=b
  for i,(p,b) in enumerate(target.items()):
   old=p.read_bytes() if p.exists() else None
   if old is not None:(backup/str(i)).write_bytes(old)
   modified[str(p)]={'backup':str(backup/str(i)) if old is not None else None,'old':digest(old) if old is not None else None,'new':digest(b)}
  (backup/'manifest.json').write_text(json.dumps(dict(previous_commit=previous,files=modified),indent=2))
  for p,b in target.items():
   p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.eurusd-tmp');tmp.write_bytes(b)
   try:tmp.replace(p)
   except PermissionError:
    # Windows may hold a non-delete-shared handle. The scheduler is stopped;
    # checked-in publication remains transactional and originals are backed up.
    if not p.is_file():raise
    assert digest(p.read_bytes())==modified[str(p)]['old'],'Concurrent file change'
    p.write_bytes(b);tmp.unlink()
   assert digest(p.read_bytes())==digest(b),'Written file mismatch'
  assert all(digest((REPO/n).read_bytes())==h for n,h in preserved.items()),'Existing dataset changed'
  names=[str(p.relative_to(REPO)).replace('\\','/') for p in target if p.is_relative_to(REPO)]
  git('-c','core.autocrlf=false','add','--',*names);git('-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--cached','--check')
  git('commit','-m','Add EURUSD M30 E2-S SELL research dashboard and nine-instrument refresh');committed=True
  git('push','origin','main');commit=git('rev-parse','HEAD')
  assert git('ls-remote','origin','refs/heads/main').split()[0]==commit,'Remote commit mismatch'
  receipt=dict(status='PUSHED',commit=commit,previous_commit=previous,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),public_url='https://my-dashboard-olo8.onrender.com/eurusd.html',previous_eight_datasets_unchanged=True,previous_data_hashes=preserved,files={str(p.relative_to(REPO)).replace('\\','/'):digest(b) for p,b in target.items() if p.is_relative_to(REPO)},task_originally_enabled=was_enabled)
  (ROOT/'deployment_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps({k:v for k,v in receipt.items() if k not in ['files','previous_data_hashes']}),flush=True)
 except Exception:
  if not committed:
   names=[str(Path(p).relative_to(REPO)).replace('\\','/') for p in modified if Path(p).is_relative_to(REPO)]
   staged=git('diff','--cached','--name-only').splitlines()
   staged=[n for n in staged if n in names]
   if staged:git('restore','--staged','--',*staged)
   for name,spec in modified.items():
    p=Path(name)
    if p.exists() and digest(p.read_bytes())==spec['new']:
     if spec['backup']:shutil.copyfile(spec['backup'],p)
     else:p.unlink()
  raise
 finally:
  if was_enabled:ps("Enable-ScheduledTask -TaskName '"+TASK+"' | Out-Null")
if __name__=='__main__':main()
