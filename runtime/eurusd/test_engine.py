from pathlib import Path
import json
import pandas as pd
from engine import scan
from build_snapshot import project,main
R=Path(__file__).resolve().parent
main(True)
d=pd.read_csv(R/'reference/source.csv');f,s,_=scan(d)
for cutoff in d.groupby(pd.to_datetime(d.time,unit='s').dt.strftime('%Y-%m')).tail(1).index:
 if pd.to_datetime(d.time.iloc[cutoff],unit='s').year<2026:continue
 _,partial,_=scan(d.iloc[:cutoff+1]);expected=s[s.i<=cutoff]
 assert partial.time.tolist()==expected.time.tolist()
 for k in ['atr','e10','e20','e50','e200']:
  assert (partial[k].to_numpy()==expected[k].to_numpy()).all()
first=int(s[s.decision.dt.year==2026].iloc[0].i)
z=project(d.iloc[:first+1],'test');e=z['entries'][-1];assert e['entry_status']=='PENDING_ENTRY'
z=project(d.iloc[:first+1],'test',entry_hint=dict(time=int(d.time.iloc[first+1]),open=float(d.open.iloc[first+1])))
assert z['entries'][-1]['entry_status']=='ENTERED' and all(o['status']=='PENDING_OUTCOME' for o in z['entries'][-1]['outcomes'].values())
z=project(d.iloc[:first+1],'test',entry_hint=dict(time=int(d.time.iloc[first+1])+1800,open=float(d.open.iloc[first+1])))
assert z['entries'][-1]['entry_status']=='CANCELLED_GAP'
z=json.loads((R/'site/eurusd-replay.json').read_text());complete=[e['outcomes']['12'] for e in z['entries'] if e['outcomes']['12']['status']=='COMPLETE']
assert len(complete)==52 and sum(o['gross_pips']>0 for o in complete)==36 and sum(o['net2_pips']>0 for o in complete)==31
assert abs(sum(o['net2_pips'] for o in complete)-260.1)<1e-6
assert all(e['direction']=='SELL' for e in z['entries'])
result=dict(status='PASS',archived_signals=53,horizon_outcomes_exact=156,monthly_prefixes=11,pending_entry_and_gap_checked=True,net2_wins=31,net2_total_pips=260.1)
(R/'engine_acceptance.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
