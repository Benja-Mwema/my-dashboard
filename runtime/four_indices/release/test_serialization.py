from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'runtime'))
from build_snapshots import build
results=[]
for stem,count in [('nas100',7),('cac40',8),('jpn225',8),('aus200',12)]:
 d=build(stem)
 decoded=json.loads(json.dumps(d,allow_nan=False))
 assert decoded==json.loads((ROOT/'runtime/site'/(stem+'-data.json')).read_text(encoding='utf-8'))
 assert decoded['candles'][0]['model_atr14'] is None
 assert decoded['validation']['archived_outcomes_exact']==2*count
 results.append(dict(symbol=stem,direct_return_is_valid_JSON=True,file_and_return_match=True,unavailable_warmup_is_null=True,archived_profiles_exact=count*2))
(ROOT/'serialization_acceptance.json').write_text(json.dumps(results,indent=2));print(json.dumps(results),flush=True)
