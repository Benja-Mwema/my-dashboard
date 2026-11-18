from pathlib import Path
from datetime import datetime, timezone
import json, subprocess, hashlib, shutil, time, sys, re
ROOT=Path(__file__).resolve().parent; APP=ROOT.parent; REPO=Path(r'D:\render_sites\my-dashboard')
TASKS=['AURUM Dashboard Refresh 15 Minutes','AURUM H1 Cluster Email']
EXPECTED={'site/assets.json':'f62a9ed204e32437f9db19919fe51df5eb48550293e6c5c4e81838574cd586cc',
 'site/aurum-ui-v1.js':'fe1c6d5a23d5e213e0c18829198d845e3311bc4464f134a41694daf03def71f0',
 'runtime/refresh_publish.py':'cca9f7e27dbc1cc04623ee5824f4bca2f42630207ed2f1c4889638ac40db71ff',
 'runtime/build_market_context.py':'27d88c968154ea55de46048904b06bb409c6820b758ec1d55ffe31b64a7057c5',
 'runtime/cluster_email/cluster_source.py':'277b4b99ed937f472d210283f0fe00b4b6129384d7df3d48760a81a9ff4c698a'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(b):return hashlib.sha256(b).hexdigest()
def run(a,timeout=240):
 r=subprocess.run(a,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
 if r.returncode:raise RuntimeError(str(a[:3])+': '+r.stderr[-2000:]+r.stdout[-1000:])
 return r.stdout.strip()
def ps(s):return run(['powershell.exe','-NoProfile','-Command',s])
def git(*args):return run(['git','-C',str(REPO),*args])
def main():
 tests=json.loads((ROOT/'ui_acceptance.json').read_text());assert len(tests)==2 and all(not t['javascript_errors'] and not t['mobile_overflow'] for t in tests)
 live=json.loads((ROOT/'site/usdjpy-data.json').read_text());assert live['health']['state']=='OK' and live['validation']['baseline_formations_exact']==55
 manifest=json.loads((ROOT/'freeze_manifest.json').read_text())
 for n,h in manifest['files'].items():assert sha(ROOT/n)==h,'Frozen file changed'
 enabled={};modified={};committed=False;previous=None;backup=ROOT/('deployment_backup_'+datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir()
 try:
  for task in TASKS:
   enabled[task]=ps("(Get-ScheduledTask -TaskName '"+task+"').Settings.Enabled").lower()=='true'
   if enabled[task]:ps("Disable-ScheduledTask -TaskName '"+task+"' | Out-Null")
  for attempt in range(90):
   running=ps("$s=New-Object -ComObject Schedule.Service; $s.Connect(); @($s.GetRunningTasks(0) | Where-Object {$_.Name -in @('AURUM Dashboard Refresh 15 Minutes','AURUM H1 Cluster Email')}).Count")
   if running=='0':break
   if attempt%3==0:print('Waiting for existing refresh to complete safely',flush=True)
   time.sleep(10)
  else:raise RuntimeError('Scheduled work still active; deployment left unchanged')
  assert not (APP/'publish_transaction.json').exists(),'Publication transaction still active'
  assert not git('status','--porcelain'),'Unrelated Git changes preserved'
  assert git('branch','--show-current')=='main'
  git('fetch','origin','main');git('merge','--ff-only','origin/main');previous=git('rev-parse','HEAD')
  for n,h in EXPECTED.items():
   p=REPO/n[5:] if n.startswith('site/') else APP/n[8:]
   assert sha(p)==h,'Concurrent shared-file change: '+n
  preserved={f.name:sha(f) for f in REPO.iterdir() if f.is_file() and (f.name.endswith('-data.json') or f.name.endswith('-replay.json') or f.name=='cluster-saved.json') and not f.name.startswith('usdjpy-')}
  # Exclude this new module from existing mail notifications; this deployment authorizes dashboard publication.
  target={APP/'cluster_email/cluster_source.py':(ROOT/'integration/cluster_source.py').read_bytes()}
  for n in ['refresh_publish.py','build_market_context.py']:
   b=(ROOT/'integration'/n).read_bytes();compile(b,n,'exec');target[APP/n]=b
  names=['usdjpy.html','usdjpy.js','usdjpy.css','usdjpy-data.json','usdjpy-replay.json','usdjpy-rules.json','usdjpy-rules.md','usdjpy-acceptance.json','assets.json','aurum-ui-v1.js']
  for n in names:target[REPO/n]=(ROOT/'site'/n).read_bytes()
  # Bust the navigation cache on every existing public page, preserving its instrument code.
  for f in REPO.glob('*.html'):
   s=f.read_text(encoding='utf-8');new=re.sub(r'(src="aurum-ui-v1\.js)(?:\?[^" ]*)?(\")',r'\1?v=usdjpy-20261118-1\2',s)
   if new!=s:target[f]=new.encode()
  context=json.loads((REPO/'market-context.json').read_text());source=json.loads((ROOT/'latest_native.json').read_text())
  current={'symbol':'USDJPY.pro','timeframe':'H1','period_seconds':3600,'state':'VERIFIED_NATIVE_CONTEXT','forming_origin':'NATIVE_H1','source_warning':None,
   'observed_at_utc':source['extracted_at_utc'],'tick_native':source['extraction']['latest_tick_epoch'],'tick_label':live['quote_broker_time'],
   'bid':source['bid'],'ask':source['ask'],'overlap_bars_verified':64,
   'completed':[{k:b[k] for k in ['time','open','high','low','close']} for b in live['candles'][-1024:]],
   'forming':live['forming'],'latest_completed_open':live['candles'][-1]['time'],'forming_open_label':datetime.fromtimestamp(live['forming']['time'],timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}
  context['assets']['usdjpy']=current;context['observed_at_utc']=datetime.now(timezone.utc).isoformat()
  target[REPO/'market-context.json']=(json.dumps(context,separators=(',',':'),allow_nan=False)+'\n').encode()
  for folder in ['', 'reference','integration']:
   for f in (ROOT/folder).iterdir():
    if f.is_file() and f.suffix in ['.py','.json','.md','.csv','.txt'] and f.name not in ['latest_native.json','deployment_receipt.json','public_verification.json']:
     target[REPO/'runtime/usdjpy'/folder/f.name]=f.read_bytes()
  frozen=Path(r'C:\Ben\mt5\research\USDJPY_H1_E1_v0_2_FROZEN_20261118')
  for p,b in list(target.items()):
   if p.is_relative_to(REPO/'runtime/usdjpy'):target[frozen/p.relative_to(REPO/'runtime/usdjpy')]=b
  state={'formula_id':'USDJPY_H1_E1_v0.2','frozen':True,'editable':False,'status':'FROZEN_RESEARCH_BASELINE','authorized_on':'2026-11-18','runtime':str(ROOT),'performance_status':'NOT_EVALUATED'}
  target[frozen/'formula_state.json']=json.dumps(state,indent=2).encode()
  for i,(p,b) in enumerate(target.items()):
   old=p.read_bytes() if p.exists() else None
   if old is not None:(backup/str(i)).write_bytes(old)
   modified[str(p)]={'backup':str(backup/str(i)) if old is not None else None,'old':digest(old) if old is not None else None,'new':digest(b)}
  (backup/'manifest.json').write_text(json.dumps({'previous_commit':previous,'files':modified},indent=2))
  for p,b in target.items():
   p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.usdjpy-tmp');tmp.write_bytes(b)
   try:tmp.replace(p)
   except PermissionError:
    assert p.is_file() and sha(p)==modified[str(p)]['old'];p.write_bytes(b);tmp.unlink()
   assert sha(p)==digest(b)
  assert all(sha(REPO/n)==h for n,h in preserved.items()),'Existing instrument data changed'
  paths=[str(p.relative_to(REPO)).replace('\\','/') for p in target if p.is_relative_to(REPO)]
  git('-c','core.autocrlf=false','add','--',*paths)
  git('-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--cached','--check')
  git('commit','-m','Freeze and deploy USDJPY H1 E1 v0.2 research dashboard');committed=True
  git('push','origin','main');commit=git('rev-parse','HEAD')
  assert git('ls-remote','origin','refs/heads/main').split()[0]==commit
  receipt={'status':'PUSHED','commit':commit,'previous_commit':previous,'at_utc':datetime.now(timezone.utc).isoformat(),
   'url':'https://my-dashboard-olo8.onrender.com/usdjpy.html','frozen':True,'baseline_formations':55,
   'previous_instrument_datasets_unchanged':len(preserved),'scheduler_original_states':enabled,
   'public_files':{n:sha(REPO/n) for n in names},'runtime_frozen_path':str(frozen)}
  (ROOT/'deployment_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt),flush=True)
 except Exception:
  if not committed:
   paths=[str(Path(p).relative_to(REPO)).replace('\\','/') for p in modified if Path(p).is_relative_to(REPO)]
   staged=[n for n in git('diff','--cached','--name-only').splitlines() if n in paths]
   if staged:git('restore','--staged','--',*staged)
   for name,spec in modified.items():
    p=Path(name)
    if p.exists() and sha(p)==spec['new']:
     if spec['backup']:shutil.copyfile(spec['backup'],p)
     else:p.unlink()
  raise
 finally:
  for task,was_enabled in enabled.items():
   if was_enabled:ps("Enable-ScheduledTask -TaskName '"+task+"' | Out-Null")
if __name__=='__main__':main()
