"""One Windows task: validate and publish all enabled AURUM instruments together."""
from pathlib import Path
import subprocess,json,datetime,sys,hashlib,traceback,shutil
ROOT=Path(__file__).resolve().parent
REPO=Path(r'D:\render_sites\my-dashboard');LOG=ROOT/'refresh_publish.log';JOURNAL=ROOT/'publish_transaction.json'
def digest(b):return hashlib.sha256(b).hexdigest()
def log(s):
 with LOG.open('a',encoding='utf-8') as f:f.write(datetime.datetime.now().isoformat()+' '+s+'\n')
def run(args):
 r=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=240)
 if r.returncode:raise RuntimeError('Command failed '+str(args[:3])+': '+r.stderr[-1800:]+r.stdout[-1000:])
 return r.stdout.rstrip()
def git(*args):return run(['git','-C',str(REPO),*args])
def recover():
 if not JOURNAL.exists():return
 j=json.loads(JOURNAL.read_text());dirty=git('status','--porcelain')
 if not dirty:JOURNAL.unlink();return
 names=[l[3:] for l in dirty.splitlines()]
 for name in names[:]:
  if name.endswith('.tmp') and name[:-4] in j['files'] and digest((REPO/name).read_bytes())==j['files'][name[:-4]]['new']:
   (REPO/name).unlink();names.remove(name)
 if any(n not in j['files'] for n in names):raise RuntimeError('Unrelated local changes; recovery stopped')
 if git('rev-parse','HEAD')!=j['head']:raise RuntimeError('HEAD changed during unfinished publication; inspect journal')
 for name in names:
  spec=j['files'][name]
  if digest((REPO/name).read_bytes()) not in (spec['old'],spec['new']):raise RuntimeError('Snapshot differs from job transaction; preserving user change')
 if names:git('restore','--staged','--',*names)
 for name in names:shutil.copyfile(Path(j['backup'])/name,REPO/name)
 JOURNAL.unlink();log('Recovered interrupted snapshot transaction; next refresh will regenerate all instruments')
def main():
 recover()
 if git('status','--porcelain'):raise RuntimeError('Repository has local changes; leaving them untouched')
 git('fetch','origin','main');git('merge','--ff-only','origin/main')
 run([sys.executable,str(ROOT/'refresh_snapshot.py')])
 gp=ROOT/'gbpjpy/gbpjpy-data.json'
 if not gp.exists() or datetime.datetime.now().timestamp()-gp.stat().st_mtime>120:run([sys.executable,str(ROOT/'gbpjpy/refresh_gbpjpy.py')])
 x=json.loads((ROOT/'site/cluster-data.json').read_text());g=json.loads(gp.read_text(encoding='utf-8'))
 assert x['version']=='AURUM_CLUSTER_H1_P1_V2_FINAL' and x['validation']['archived_outcomes_exact']
 assert g['version']=='GBPJPY_H1_R1_v1.0' and len(g['signals'])==len({s['id'] for s in g['signals']})
 assert all(s['entry_time']<=g['quote_broker_time'] for s in g['signals'])
 x['refresh_mode']='Automatic snapshot refresh every 15 minutes';g['publication_mode']='Automatic publication every 15 minutes; this page displays a snapshot, not a tick stream'
 bundle={'cluster-data.json':x,'gbpjpy-data.json':g};times={'XAUUSD_asof':x['data_asof'],'GBPJPY_asof':g['candles'][-1]['close_time']}
 config=json.loads((ROOT/'audcad/config.json').read_text());bundle['audcad-config.json']=config
 if config['enabled']:
  run([sys.executable,str(ROOT/'audcad/refresh_audcad.py')]);a=json.loads((ROOT/'audcad/audcad-data.json').read_text(encoding='utf-8'))
  assert a['version']=='AUDCAD_H1_BUY_SELL_V1_0' and a['data_quality_state']=='OK'
  assert len(a['entries'])==len({e['id'] for e in a['entries']})
  assert all(e['signal_available_at']<=a['quote_broker_time'] for e in a['entries'])
  bundle['audcad-data.json']=a;times['AUDCAD_asof']=a['latest_completed_h1']
 # Serialize every output before changing any published file.
 encoded={n:(json.dumps(d,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode() for n,d in bundle.items()}
 backup=ROOT/'publication_backup';backup.mkdir(exist_ok=True);files={}
 for n,b in encoded.items():
  old=(REPO/n).read_bytes();(backup/n).write_bytes(old);files[n]={'old':digest(old),'new':digest(b)}
 JOURNAL.write_text(json.dumps({'head':git('rev-parse','HEAD'),'backup':str(backup),'files':files}))
 try:
  for n,b in encoded.items():
   tmp=REPO/(n+'.tmp');tmp.write_bytes(b);tmp.replace(REPO/n)
  git('add','--',*encoded)
  if git('diff','--cached','--name-only'):git('diff','--cached','--check');git('commit','-m','Refresh bundled AURUM research snapshots')
 except Exception:
  recover();raise
 JOURNAL.unlink(missing_ok=True)
 git('push','origin','main')
 result=dict(status='published',completed_at=datetime.datetime.now().astimezone().isoformat(),commit=git('rev-parse','HEAD'),**times)
 (ROOT/'refresh_publish_status.json').write_text(json.dumps(result,indent=2));log(json.dumps(result));print(json.dumps(result))
if __name__=='__main__':
 try:main()
 except Exception as e:
  log('FAILED '+str(e));(ROOT/'refresh_publish_status.json').write_text(json.dumps({'status':'failed','error':str(e),'at':datetime.datetime.now().isoformat()}));traceback.print_exc();sys.exit(1)
