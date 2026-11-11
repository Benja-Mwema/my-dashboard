"""Scheduled read-only MT5 refresh and scoped snapshot publication."""
from pathlib import Path
import subprocess,json,datetime,sys,os,traceback
ROOT=Path(__file__).resolve().parent
REPO=Path(r'D:\render_sites\my-dashboard')
LOG=ROOT/'refresh_publish.log'
def log(message):
 with LOG.open('a',encoding='utf-8') as f:f.write(datetime.datetime.now().isoformat()+' '+message+'\n')
def run(args,cwd=None):
 r=subprocess.run(args,cwd=cwd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=240)
 if r.returncode:raise RuntimeError('Command failed: '+str(args[:3])+' '+r.stderr[-2000:]+r.stdout[-1000:])
 return r.stdout.strip()
def git(*args):return run(['git','-C',str(REPO),*args])
def main():
 if git('status','--porcelain'):raise RuntimeError('Repository has local changes; leaving them untouched')
 git('fetch','origin','main');git('merge','--ff-only','origin/main')
 run([sys.executable,str(ROOT/'refresh_snapshot.py')])
 gp=ROOT/'gbpjpy'/'gbpjpy-data.json'
 if not gp.exists() or datetime.datetime.now().timestamp()-gp.stat().st_mtime>120:
  run([sys.executable,str(ROOT/'gbpjpy'/'refresh_gbpjpy.py')])
 x=json.loads((ROOT/'site/cluster-data.json').read_text());g=json.loads(gp.read_text(encoding='utf-8'))
 assert x['version']=='AURUM_CLUSTER_H1_P1_V2_FINAL' and x['validation']['archived_outcomes_exact']
 assert g['version']=='GBPJPY_H1_R1_v1.0' and g['symbol'].startswith('GBPJPY')
 assert len({s['id'] for s in g['signals']})==len(g['signals'])
 assert all(s['entry_time']<=g['quote_broker_time'] for s in g['signals'])
 x['refresh_mode']='Automatic snapshot refresh every 15 minutes'
 g['publication_mode']='Automatic publication every 15 minutes; this page displays a snapshot, not a tick stream'
 for name,data in [('cluster-data.json',x),('gbpjpy-data.json',g)]:
  temp=REPO/(name+'.tmp');temp.write_bytes((json.dumps(data,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode());temp.replace(REPO/name)
 git('add','--','cluster-data.json','gbpjpy-data.json')
 if git('diff','--cached','--name-only'):
  git('diff','--cached','--check');git('commit','-m','Refresh AURUM published instrument snapshots')
 git('push','origin','main')
 result={'status':'published','completed_at':datetime.datetime.now().astimezone().isoformat(),'commit':git('rev-parse','HEAD'),'XAUUSD_asof':x['data_asof'],'GBPJPY_asof':g['candles'][-1]['close_time']}
 (ROOT/'refresh_publish_status.json').write_text(json.dumps(result,indent=2));log(json.dumps(result));print(json.dumps(result))
if __name__=='__main__':
 try:main()
 except Exception as e:
  log('FAILED '+str(e));(ROOT/'refresh_publish_status.json').write_text(json.dumps({'status':'failed','error':str(e),'at':datetime.datetime.now().isoformat()}));traceback.print_exc();sys.exit(1)
