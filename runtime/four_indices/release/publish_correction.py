from pathlib import Path
import json,hashlib,datetime,shutil
from deploy import ps,git
from prepare_preview import bust
ROOT=Path(__file__).resolve().parent;APP=ROOT.parent;REPO=Path(r'D:\render_sites\my-dashboard');TASK='AURUM Dashboard Refresh 15 Minutes'
def sha(b):return hashlib.sha256(b).hexdigest()
assert len(json.loads((ROOT/'serialization_acceptance.json').read_text()))==4
was_enabled=ps("(Get-ScheduledTask -TaskName '"+TASK+"').Settings.Enabled").lower()=='true'
ps("Disable-ScheduledTask -TaskName '"+TASK+"' | Out-Null")
committed=False;modified={};backup=ROOT/('serialization_backup_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir()
try:
 assert ps("$svc=New-Object -ComObject Schedule.Service; $svc.Connect(); @($svc.GetRunningTasks(0) | Where-Object { $_.Name -eq '"+TASK+"' }).Count")=='0','Refresh still running'
 assert not (APP/'publish_transaction.json').exists()
 assert not git('status','--porcelain')
 git('fetch','origin','main');git('merge','--ff-only','origin/main');previous=git('rev-parse','HEAD')
 receipt=json.loads((ROOT/'deployment_receipt.json').read_text());rel='runtime/four_indices/build_snapshots.py';old=(REPO/rel).read_bytes()
 assert sha(old)==receipt['files'][rel] and (APP/'four_indices/build_snapshots.py').read_bytes()==old
 new=(ROOT/'runtime/build_snapshots.py').read_bytes()
 expected=old.decode().replace(" atomic(ROOT/'site'/(stem+'-data.json'),out)"," # The scheduler consumes this return value directly; normalize unavailable\n # warm-up indicators here as well as in the on-disk JSON writer.\n out=clean(out)\n atomic(ROOT/'site'/(stem+'-data.json'),out)")
 assert new.decode().replace('\r\n','\n')==expected.replace('\r\n','\n')
 compile(new.decode(),rel,'exec')
 target={REPO/rel:new,APP/'four_indices/build_snapshots.py':new}
 for p in (ROOT/'site').glob('*.html'):
  assert sha((REPO/p.name).read_bytes())==receipt['files'][p.name],'Page changed concurrently'
  target[REPO/p.name]=bust(p.read_text(encoding='utf-8-sig')).encode('utf-8')
 for n in ['test_serialization.py','serialization_acceptance.json','publish_correction.py','deploy.py','test_ui.py','verify_release.py']:target[REPO/'runtime/four_indices/release'/n]=(ROOT/n).read_bytes()
 for i,(p,b) in enumerate(target.items()):
  old_b=p.read_bytes() if p.exists() else None
  if old_b is not None:(backup/str(i)).write_bytes(old_b)
  modified[p]=(backup/str(i) if old_b is not None else None,sha(b))
  p.parent.mkdir(parents=True,exist_ok=True);temp=p.with_suffix(p.suffix+'.fix-tmp');temp.write_bytes(b);temp.replace(p)
 names=[str(p.relative_to(REPO)).replace('\\','/') for p in target if p.is_relative_to(REPO)]
 git('-c','core.autocrlf=false','add','--',*names);git('-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--cached','--check')
 git('commit','-m','Normalize index JSON and preserve UTF-8 page text on Windows');committed=True;git('push','origin','main');commit=git('rev-parse','HEAD')
 assert git('ls-remote','origin','refs/heads/main').split()[0]==commit
 result=dict(status='PUSHED',commit=commit,previous_commit=previous,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),reason='Normalize direct builder return to valid JSON and preserve UTF-8 page text on Windows.',archived_outcomes_unchanged=70,model_hash_unchanged=True,files={str(p.relative_to(REPO)).replace('\\','/'):sha(b) for p,b in target.items() if p.is_relative_to(REPO)})
 (ROOT/'runtime_correction_receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
except Exception:
 if not committed:
  staged=[str(p.relative_to(REPO)).replace('\\','/') for p in modified if p.is_relative_to(REPO)]
  if staged:git('restore','--staged','--',*staged)
  for p,(old_file,h) in modified.items():
   if p.exists() and sha(p.read_bytes())==h:
    if old_file:shutil.copyfile(old_file,p)
    else:p.unlink()
 raise
finally:
 if was_enabled:ps("Enable-ScheduledTask -TaskName '"+TASK+"' | Out-Null")
print(ps("Start-ScheduledTask -TaskName '"+TASK+"'; Get-ScheduledTask -TaskName '"+TASK+"' | Select-Object State,@{Name='Enabled';Expression={$_.Settings.Enabled}} | ConvertTo-Json -Compress"),flush=True)
