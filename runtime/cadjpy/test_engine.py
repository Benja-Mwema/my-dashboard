from pathlib import Path
import json,pandas as pd
from engine import scan
from build_snapshot import project
p=Path(__file__).parent;raw=pd.read_csv(p/'reference/source.csv');f,s,_=scan(raw)
for cut in [13000,16000,len(raw)-40]:
 _,prefix,_=scan(raw.iloc[:cut]);pd.testing.assert_frame_equal(prefix.reset_index(drop=True),s[s.i<cut].reset_index(drop=True))
sig=s[s.decision.dt.year==2026].iloc[-1];i=int(sig.i)
pending=project(raw.iloc[:i+1],'test')['entries'][-1];assert pending['entry_status']=='PENDING_ENTRY'
hint=raw.iloc[i+1].to_dict();entered=project(raw.iloc[:i+1],'test',entry_hint=hint)['entries'][-1]
assert entered['entry_status']=='ENTERED' and entered['outcomes']['12']['gross_pips'] is None
hint['time']+=3600;cancel=project(raw.iloc[:i+1],'test',entry_hint=hint)['entries'][-1];assert cancel['entry_status']=='CANCELLED_GAP'
partial=project(raw.iloc[:i+6],'test')['entries'][-1];assert partial['outcomes']['12']['status']=='PENDING_OUTCOME' and partial['outcomes']['12']['adverse35'] is None
assert partial['outcomes']['12']['observed_bars']==5
print(json.dumps(dict(prefix_checks=3,pending_entry=True,next_open_hint=True,gap_cancel=True,pending_not_scored=True)))
