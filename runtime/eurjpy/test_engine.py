from pathlib import Path
import json,pandas as pd
from engine import scan
from build_snapshot import project,main
p=Path(__file__).parent;raw=pd.read_csv(p/'reference/source.csv');f,s,_=scan(raw)
for cut in [12432,17000,len(raw)-40]:
 _,prefix,_=scan(raw.iloc[:cut]);pd.testing.assert_frame_equal(prefix.reset_index(drop=True),s[s.i<cut].reset_index(drop=True))
sig=s[s.decision.dt.year==2026].iloc[-1];i=int(sig.i)
pending=project(raw.iloc[:i+1],'test')['entries'][-1];assert pending['entry_status']=='PENDING_ENTRY'
hint=raw.iloc[i+1].to_dict();entered=project(raw.iloc[:i+1],'test',entry_hint=hint)['entries'][-1]
assert entered['entry_status']=='ENTERED' and entered['outcomes']['12']['gross_pips'] is None
hint['time']+=1800;cancel=project(raw.iloc[:i+1],'test',entry_hint=hint)['entries'][-1];assert cancel['entry_status']=='CANCELLED_GAP'
partial=project(raw.iloc[:i+6],'test')['entries'][-1];assert partial['outcomes']['12']['status']=='PENDING_OUTCOME' and partial['outcomes']['12']['adverse35'] is None
assert partial['outcomes']['12']['observed_bars']==5
r=project(raw,'test');ref=pd.read_csv(p/'reference/signals.csv');assert len(r['entries'])==119
for e,old in zip(r['entries'],ref.itertuples()):
 assert e['signal_available_at']==old.decision_time and e['direction']==old.side
 for h in (12,24):
  o=e['outcomes'][str(h)]
  for key in ['gross_pips','mfe_pips','mae_pips','mfe_atr','mae_atr']:assert abs(o[key]-getattr(old,f'h{h}_{key}'))<1e-7
  assert o['first_hit_2atr_vs_1atr']==getattr(old,f'h{h}_path')
assert sum(e['outcomes']['12']['gross_pips']>0 for e in r['entries'])==66
assert sum(e['outcomes']['12']['gross_pips']>2 for e in r['entries'])==59
assert sum(e['outcomes']['24']['gross_pips']==0 for e in r['entries'])==1
assert all(pd.Timestamp(c['close_time'])-pd.Timestamp(c['open_time'])==pd.Timedelta(minutes=30) for c in r['candles'])
assert all('1800' in e['predicates'][-1]['condition'] for e in r['entries'])
proof=dict(prefix_checks=3,pending_entry=True,next_open_hint=True,gap_cancel=True,pending_not_scored=True,signals=119,horizon_outcomes_exact=238,first_hit_diagnostics_exact=238,bar_duration_seconds=1800)
(p/'engine_acceptance.json').write_text(json.dumps(proof,indent=2));print(json.dumps(proof))
