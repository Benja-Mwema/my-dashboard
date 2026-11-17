from pathlib import Path
import json,hashlib,shutil,re,subprocess,sys
R=Path(__file__).resolve().parent;A=R.parent;REPO=Path(r'D:\render_sites\my-dashboard')
shared=['aurum-ui-v1.js','aurum-workspace-v2.js','aurum-charts-v3.js','assets.json']
expected={}
for n in shared:
 p=REPO/n;assert p.read_text(encoding='utf-8').strip()==(R/'inspection/site'/n).read_text(encoding='utf-8').strip(),'Shared site source changed: '+n
 expected['site/'+n]=hashlib.sha256(p.read_bytes()).hexdigest()
for n in ['refresh_publish.py','build_market_context.py']:
 p=A/n;assert p.read_text(encoding='utf-8').strip()==(R/'inspection/shared'/n).read_text(encoding='utf-8').strip(),'Shared backend source changed: '+n
 expected['backend/'+n]=hashlib.sha256(p.read_bytes()).hexdigest()
for p in REPO.glob('*.html'):
 s=p.read_text(encoding='utf-8')
 if 'aurum-charts-v3.js' not in s:continue
 for name in ['aurum-ui-v1.js','aurum-workspace-v2.js','aurum-charts-v3.js']:
  s=re.sub(re.escape(name)+r'(?:\?[^"\s]*)?',name+'?v=eurusd-e2s-1',s)
 (R/'site'/p.name).write_text(s,encoding='utf-8');expected['site/'+p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
(R/'expected_shared.json').write_text(json.dumps(expected,indent=2))
preview=R/'preview';preview.mkdir(exist_ok=True)
for p in REPO.iterdir():
 if p.is_file() and p.suffix in ['.html','.css','.js','.json','.svg','.png','.ico']:shutil.copyfile(p,preview/p.name)
for p in (R/'site').iterdir():
 if p.is_file():shutil.copyfile(p,preview/p.name)
sys.path.insert(0,str(R/'integration'))
import build_market_context as ctx
ctx.REPO=preview
context=ctx.build();(preview/'market-context.json').write_text(json.dumps(context))
print(json.dumps({k:v['state'] for k,v in context['assets'].items()}),flush=True)
