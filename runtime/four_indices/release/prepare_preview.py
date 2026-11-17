from pathlib import Path
import shutil,re,json,importlib.util,hashlib
ROOT=Path(__file__).resolve().parent
REPO=Path(r'D:\render_sites\my-dashboard')
def bust(text):
 return re.sub(r'((?:aurum-ui-v1\.(?:js|css)|aurum-workspace-v2\.js|aurum-charts-v3\.js))(?:\?[^"\s<>]*)?',r'\1?v=indices-20261117-1',text)
def main():
 preview=ROOT/'preview';preview.mkdir(exist_ok=True)
 for p in REPO.iterdir():
  if p.is_file() and p.suffix.lower() in ['.html','.css','.js','.json','.ico','.svg','.png']:
   shutil.copyfile(p,preview/p.name)
 for p in (ROOT/'runtime/site').iterdir():
  if p.suffix=='.json':shutil.copyfile(p,ROOT/'site'/p.name)
 accepted={}
 for stem,count in [('nas100',7),('cac40',8),('jpn225',8),('aus200',12)]:
  saved=json.loads((ROOT/'site'/(stem+'-replay.json')).read_text());live=json.loads((ROOT/'site'/(stem+'-data.json')).read_text())
  v=saved['validation'];assert v['archived_signals_exact']==count and v['archived_outcomes_exact']==2*count and len(v['causal_prefix_checks'])==3
  assert live['validation']['archived_outcomes_exact']==2*count
  accepted[stem]=dict(offline=v,live=live['validation'],latest_completed_h1=live['latest_completed_h1'],health=live['health']['state'])
 (ROOT/'engine_acceptance.json').write_text(json.dumps(accepted,indent=2))
 for p in (ROOT/'site').iterdir():
  if p.is_file():shutil.copyfile(p,preview/p.name)
 for p in preview.glob('*.html'):
  txt=bust(p.read_text(encoding='utf-8-sig'));p.write_text(txt,encoding='utf-8')
 spec=importlib.util.spec_from_file_location('preview_context',ROOT/'integration/build_market_context.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);mod.REPO=preview
 d=mod.build();assert all(d['assets'][k]['state']=='VERIFIED_NATIVE_CONTEXT' for k in ['nas100','cac40','jpn225','aus200'])
 (preview/'market-context.json').write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
 print(json.dumps({k:{a:v.get(a) for a in ['state','forming_open_label','reason']} for k,v in d['assets'].items()}),flush=True)
if __name__=='__main__':main()
