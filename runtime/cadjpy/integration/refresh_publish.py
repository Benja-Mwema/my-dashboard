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

def publish_current_context():
 # Fast chart publication precedes expensive research replay. Same task,
 # same all-instrument context snapshot, same recoverable Git transaction.
 from build_market_context import build
 context=build();name='market-context.json'
 raw=(json.dumps(context,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
 old=(REPO/name).read_bytes();backup=ROOT/'publication_backup';backup.mkdir(exist_ok=True)
 (backup/name).write_bytes(old)
 JOURNAL.write_text(json.dumps({'head':git('rev-parse','HEAD'),'backup':str(backup),
   'files':{name:{'old':digest(old),'new':digest(raw)}}}))
 try:
  tmp=REPO/(name+'.tmp');tmp.write_bytes(raw);tmp.replace(REPO/name)
  git('add','--',name);git('diff','--cached','--check')
  if git('diff','--cached','--name-only'):git('commit','-m','Refresh current chart bars before research replay')
 except Exception:
  recover();raise
 JOURNAL.unlink(missing_ok=True);git('push','origin','main')
 receipt={'status':'published','completed_at':datetime.datetime.now().astimezone().isoformat(),
  'source_observed_at_utc':context['observed_at_utc'],'commit':git('rev-parse','HEAD'),
  'states':{k:v['state'] for k,v in context['assets'].items()}}
 (ROOT/'chart_context_publish_status.json').write_text(json.dumps(receipt,indent=2))
 log('CURRENT_BAR_FAST_PUBLICATION '+json.dumps(receipt));print(json.dumps(receipt),flush=True)
 return receipt

def main():
 recover()
 if git('status','--porcelain'):raise RuntimeError('Repository has local changes; leaving them untouched')
 git('fetch','origin','main');git('merge','--ff-only','origin/main')
 try:publish_current_context()
 except Exception as error:log('CURRENT_BAR_FAST_PUBLICATION_FAILED '+repr(error))
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
 # Optional WS30 module joins the SAME atomic 15-minute bundle after its
 # initial public files have been created through the controlled release.
 # A WS30 failure must never erase or block Gold/GBPJPY/AUDCAD updates.
 ws30_config=ROOT/'ws30/config.json'
 if ws30_config.exists():
  wc=json.loads(ws30_config.read_text(encoding='utf-8'))
  if wc.get('enabled',False):
   try:
    if not (REPO/'ws30-data.json').is_file():
     raise RuntimeError('WS30 initial public file absent; run controlled first-file release')
    if wc.get('broker_orders_enabled') is not False or wc.get('paper_only') is not True:
     raise RuntimeError('WS30 order safety configuration mismatch')
    run([sys.executable,str(ROOT/'ws30/build_snapshot_v1.py')])
    run([sys.executable,str(ROOT/'ws30/validate_snapshot_schema_v1.py')])
    w=json.loads((ROOT/'ws30/site/ws30-data.json').read_text(encoding='utf-8'))
    assert w['meta']['symbol']=='WS30.pro' and w['meta']['broker_orders_enabled'] is False
    assert w['meta']['rule_manifest_hashes']==wc['four_rule_manifest_hashes']
    assert len(w['signals'])==189 and len(w['candles'])>=17000
    assert w['health']['paper_journal_validated'] is True
    assert w['health']['source_health_state']=='OK_SOURCE_OVERLAP_CONFIRMED'
    assert w['health']['state'] in ('OK','STALE')
    bundle['ws30-data.json']=w
    times['WS30_asof']=w['health']['last_confirmed_broker_H1']
   except Exception as error:
    log('WS30_SUBMODULE_FAILED_RETENTION_OF_PREVIOUS_VERIFIED_SNAPSHOT '+repr(error))
    (ROOT/'ws30/publication_warning.json').write_text(json.dumps({
       'status':'WS30_UPDATE_UNAVAILABLE_OTHER_ASSETS_CONTINUE',
       'reason':str(error),'at':datetime.datetime.now().astimezone().isoformat()},indent=2))
 # Optional frozen DAX40 analytics joins the existing publication transaction.
 dax40_config=ROOT/'dax40/config.json'
 if dax40_config.exists():
  dc=json.loads(dax40_config.read_text(encoding='utf-8'))
  if dc.get('enabled',False):
   try:
    assert dc.get('broker_orders_enabled') is False and dc.get('paper_only') is True
    assert (REPO/'dax40-data.json').is_file(),'DAX40 initial controlled release missing'
    dr=subprocess.run([sys.executable,str(ROOT/'dax40/build_snapshot.py')],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=600)
    if dr.returncode:raise RuntimeError(dr.stderr[-1500:]+dr.stdout[-1000:])
    dx=json.loads((ROOT/'dax40/site/dax40-data.json').read_text(encoding='utf-8'))
    assert dx['version']=='DAX40-DASHBOARD-1.0' and dx['symbol']=='DAX40.pro'
    assert dx['meta']['broker_orders_enabled'] is False and dx['meta']['market_gating'] is False
    assert dx['validation']['archived_signals_exact']==670 and dx['validation']['archived_closed_outcomes_exact']==669
    assert len(dx['signals'])==len({s['id'] for s in dx['signals']})
    bundle['dax40-data.json']=dx
    times['DAX40_asof']=datetime.datetime.fromtimestamp(dx['meta']['source_last']['H1']+3600,datetime.timezone.utc).isoformat()
    (ROOT/'dax40/publication_warning.json').unlink(missing_ok=True)
   except Exception as error:
    log('DAX40_SUBMODULE_FAILED_PREVIOUS_SNAPSHOT_RETAINED '+repr(error))
    (ROOT/'dax40/publication_warning.json').write_text(json.dumps({'status':'DAX40_UPDATE_UNAVAILABLE_OTHER_ASSETS_CONTINUE','reason':str(error),'at':datetime.datetime.now().astimezone().isoformat()},indent=2))
 # CADJPY E1 H1: isolated failure retains previous verified snapshot.
 cadjpy_config=ROOT/'cadjpy/config.json'
 if cadjpy_config.exists() and json.loads(cadjpy_config.read_text()).get('enabled',False):
  try:
   assert (REPO/'cadjpy-data.json').exists(),'Initial CADJPY release missing'
   run([sys.executable,str(ROOT/'cadjpy/build_snapshot.py')])
   cj=json.loads((ROOT/'cadjpy/site/cadjpy-data.json').read_text(encoding='utf-8'))
   assert cj['version']=='CADJPY_H1_E1_V0_1' and cj['symbol']=='CADJPY.pro'
   assert cj['meta']['broker_orders_enabled'] is False and cj['validation']['archived_signals_exact']==49
   assert len(cj['entries'])==len({e['id'] for e in cj['entries']})
   bundle['cadjpy-data.json']=cj;times['CADJPY_asof']=cj['latest_completed_h1']
   (ROOT/'cadjpy/publication_warning.json').unlink(missing_ok=True)
  except Exception as error:
   log('CADJPY_SUBMODULE_FAILED_PREVIOUS_SNAPSHOT_RETAINED '+repr(error))
   (ROOT/'cadjpy/publication_warning.json').write_text(json.dumps({'status':'CADJPY_UPDATE_UNAVAILABLE_OTHER_ASSETS_CONTINUE','reason':str(error),'at':datetime.datetime.now().astimezone().isoformat()},indent=2))
 # Current market chart context is separate from frozen signal inputs.
 from build_market_context import build as build_market_context
 bundle['market-context.json']=build_market_context()
 times['chart_context_states']={k:v['state'] for k,v in bundle['market-context.json']['assets'].items()}
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
