from pathlib import Path
import subprocess,sys,json,shutil,importlib.util
ROOT=Path(__file__).resolve().parent;PRE=ROOT/'preview';REPO=Path(r'D:\render_sites\my-dashboard')
for name,args in [('build_snapshot.py',['--offline']),('test_engine.py',[]),('build_snapshot.py',[])]:
 r=subprocess.run([sys.executable,str(ROOT/name),*args],capture_output=True,text=True,encoding='utf-8');print(r.stdout,flush=True);assert r.returncode==0,r.stderr
PRE.mkdir(exist_ok=True)
for p in REPO.iterdir():
 if p.is_file() and p.suffix in ['.html','.js','.css','.json']:shutil.copyfile(p,PRE/p.name)
for p in (ROOT/'site').iterdir():
 if p.is_file():shutil.copyfile(p,PRE/p.name)
sp=importlib.util.spec_from_file_location('candidate_context',ROOT/'integration/build_market_context.py');ctx=importlib.util.module_from_spec(sp);sp.loader.exec_module(ctx);ctx.REPO=PRE
context=ctx.build();assert len(context['assets'])==8
assert all(v['state']=='VERIFIED_NATIVE_CONTEXT' for v in context['assets'].values()),{k:v.get('reason') for k,v in context['assets'].items()}
assert context['assets']['gbpusd']['period_seconds']==1800
(PRE/'market-context.json').write_text(json.dumps(context,separators=(',',':')));(ROOT/'site/market-context.json').write_text(json.dumps(context,separators=(',',':')))
print(json.dumps({'preview_ready':True,'contexts':{k:{'state':v['state'],'timeframe':v['timeframe'],'forming_open_label':v['forming_open_label']} for k,v in context['assets'].items()}}),flush=True)
