from pathlib import Path
import subprocess,json,hashlib,time,shutil,datetime
from prepare_preview import bust
ROOT=Path(__file__).resolve().parent;APP=ROOT.parent;REPO=Path(r'D:\render_sites\my-dashboard');TASK='AURUM Dashboard Refresh 15 Minutes'
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=240)
 if p.returncode:raise RuntimeError(p.stderr[-3500:]+p.stdout[-1000:])
 return p.stdout.strip()
def ps(s):return run(['powershell.exe','-NoProfile','-Command',s])
def git(*args):return run(['git','-C',str(REPO),*args])
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 assert len(json.loads((ROOT/'ui_acceptance.json').read_text()))==13
 validation=json.loads((ROOT/'engine_acceptance.json').read_text())
 assert sum(x['offline']['archived_outcomes_exact'] for x in validation.values())==70
 assert sum(len(x['offline']['causal_prefix_checks']) for x in validation.values())==12
 was_enabled=ps("(Get-ScheduledTask -TaskName '"+TASK+"').Settings.Enabled").lower()=='true'
 backup=ROOT/('deployment_backup_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir()
 modified={};committed=False;previous=None
 ps("Disable-ScheduledTask -TaskName '"+TASK+"' | Out-Null")
 try:
  for j in range(70):
   running=ps("$svc=New-Object -ComObject Schedule.Service; $svc.Connect(); @($svc.GetRunningTasks(0) | Where-Object { $_.Name -eq '"+TASK+"' }).Count")
   if running=='0':break
   if j%3==0:print('Waiting for the current publication to finish',flush=True)
   time.sleep(10)
  else:raise RuntimeError('Scheduled refresh still active; no deployment changes made')
  assert not (APP/'publish_transaction.json').exists(),'Publisher journal unresolved'
  assert not git('status','--porcelain'),'Existing checkout changes preserved'
  assert git('branch','--show-current')=='main'
  git('fetch','origin','main');git('merge','--ff-only','origin/main');previous=git('rev-parse','HEAD')
  for name,digest in json.loads((ROOT/'expected_shared.json').read_text()).items():
   p=REPO/name[5:] if name.startswith('repo/') else APP/name[9:]
   assert sha(p.read_bytes())==digest,'Shared source changed: '+name
  preserved={p.name:sha(p.read_bytes()) for p in REPO.iterdir() if p.is_file() and (p.name.endswith('-data.json') or p.name.endswith('-replay.json') or p.name=='cluster-saved.json')}
  target={REPO/p.name:p.read_bytes() for p in (ROOT/'site').iterdir() if p.is_file()}
  for p in REPO.glob('*.html'):
   current=target.get(p,p.read_bytes()).decode('utf-8-sig');changed=bust(current).encode()
   if changed!=p.read_bytes() or p in target:target[p]=changed
  for p in (ROOT/'site').glob('*.html'):target[REPO/p.name]=bust(p.read_text()).encode()
  # Runtime source is versioned; private native-bar caches remain on the workstation.
  runtime=ROOT/'runtime'
  for p in runtime.rglob('*'):
   if not p.is_file() or '__pycache__' in p.parts:continue
   rel=p.relative_to(runtime)
   if p.suffix in ['.py','.json','.csv'] and not p.name.endswith('_build_error.json'):
    target[APP/'four_indices'/rel]=p.read_bytes()
   if rel.parts[0] not in ['site','cache'] and not p.name.endswith(('_build_error.json','_first_seen.json')) and p.suffix in ['.py','.json']:
    target[REPO/'runtime/four_indices'/rel]=p.read_bytes()
  for name in ['prepare_preview.py','test_ui.py','deploy.py','verify_release.py','engine_acceptance.json','ui_acceptance.json','expected_shared.json','DEPLOYMENT.md']:
   target[REPO/'runtime/four_indices/release'/name]=(ROOT/name).read_bytes()
  for name in ['refresh_publish.py','build_market_context.py']:
   b=(ROOT/'integration'/name).read_bytes();compile(b.decode(),name,'exec');target[APP/name]=b;target[REPO/'runtime/four_indices/integration'/name]=b
  target[REPO/'market-context.json']=(ROOT/'preview/market-context.json').read_bytes()
  marker=dict(release='AURUM_FOUR_INDICES_20261117_1',model_hash=json.loads((runtime/'candidates.json').read_text())['model_hash'],archived_entries=35,archived_outcome_profiles=70,category_order=['metals','indices','currencies'],instrument_count=13,validation_status='RESEARCH_CANDIDATES_INDEPENDENT_VALIDATION_PENDING',created_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
  target[REPO/'four-indices-release.json']=(json.dumps(marker,indent=2)+'\n').encode()
  for i,(p,b) in enumerate(target.items()):
   old=p.read_bytes() if p.exists() else None
   if old is not None:(backup/str(i)).write_bytes(old)
   modified[str(p)]={'backup':str(backup/str(i)) if old is not None else None,'old':sha(old) if old is not None else None,'new':sha(b)}
  (backup/'manifest.json').write_text(json.dumps(dict(previous_commit=previous,files=modified),indent=2))
  for p,b in target.items():
   p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.indices-tmp');tmp.write_bytes(b)
   try:tmp.replace(p)
   except PermissionError:
    assert p.is_file() and sha(p.read_bytes())==modified[str(p)]['old'],'Concurrent modification'
    p.write_bytes(b);tmp.unlink()
   assert sha(p.read_bytes())==sha(b)
  assert all(sha((REPO/n).read_bytes())==h for n,h in preserved.items()),'Existing instrument data changed'
  names=[str(p.relative_to(REPO)).replace('\\','/') for p in target if p.is_relative_to(REPO)]
  git('-c','core.autocrlf=false','add','--',*names)
  # Frozen source bytes are hash-locked, including the original trailing blank line.
  git('-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--cached','--check','--','.',':(exclude)runtime/four_indices/frozen/**')
  git('commit','-m','Deploy four index research candidates and group Metals Indices Currencies');committed=True
  git('push','origin','main');commit=git('rev-parse','HEAD')
  assert git('ls-remote','origin','refs/heads/main').split()[0]==commit
  result=dict(status='PUSHED',commit=commit,previous_commit=previous,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),previous_instrument_data_unchanged=True,previous_data_hashes=preserved,task_originally_enabled=was_enabled,files={str(p.relative_to(REPO)).replace('\\','/'):sha(b) for p,b in target.items() if p.is_relative_to(REPO)},backup=str(backup))
  (ROOT/'deployment_receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['files','previous_data_hashes']}),flush=True)
 except Exception:
  if not committed:
   names=[str(Path(p).relative_to(REPO)).replace('\\','/') for p in modified if Path(p).is_relative_to(REPO)]
   staged=[n for n in git('diff','--cached','--name-only').splitlines() if n in names]
   if staged:git('restore','--staged','--',*staged)
   for name,spec in modified.items():
    p=Path(name)
    if p.exists() and sha(p.read_bytes())==spec['new']:
     if spec['backup']:shutil.copyfile(spec['backup'],p)
     else:p.unlink()
  raise
 finally:
  if was_enabled:ps("Enable-ScheduledTask -TaskName '"+TASK+"' | Out-Null")
if __name__=='__main__':main()
