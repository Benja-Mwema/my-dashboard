import json, unittest
from pathlib import Path
from gbpjpy_r1 import *
ROOT=Path(__file__).parent
RAW=json.loads((ROOT/'frozen_bars.json').read_text());CUT=RAW[-1]['time']+3600
class FrozenTests(unittest.TestCase):
 def test_reconciliation(self):
  d=build(RAW,CUT);s=d['summary'];self.assertEqual([s[k] for k in ('signals','completed','open','nonnegative','losses')],[15,14,1,6,8]);self.assertAlmostEqual(s['gross_pips'],181.930303198,8)
  original=json.loads((ROOT/'expected_signals.json').read_text())
  self.assertEqual(len(original),len(d['signals']))
  for got,want in zip(d['signals'],original):
   self.assertEqual(got['candles'][0]['time'],RAW[want['i']]['time']);self.assertEqual(got['entry_reference'],want['reference']);self.assertEqual(got['entry_time'],RAW[want['decision_i']]['time']+3600)
 def test_touch_references(self):
  got=build(RAW,CUT)["signals"];expected=json.loads((ROOT/"expected_touches.json").read_text())
  for s,e in zip(got,expected):
   if e["exit"] is None:self.assertIsNone(s["exit"])
   else:self.assertAlmostEqual(s["exit"]["reference_price"],e["exit"],10)
 def test_initialization(self):
  bars=indicators(RAW,CUT)
  for a,b in zip(RAW,bars):
   for n in (10,20):self.assertAlmostEqual(a[f'ema{n}'],b[f'ema{n}'],10)
 def test_forming_and_prefix(self):
  full=build(RAW,CUT)
  for s in full['signals']:
   partial=build(RAW,s['entry_time']-1)
   self.assertNotIn(s['id'],[x['id'] for x in partial['signals']])
   closed=build(RAW,s['entry_time'])
   self.assertEqual([x['id'] for x in closed['signals']],[x['id'] for x in full['signals'] if x['entry_time']<=s['entry_time']])
 def test_gap_and_rejection_no_roll(self):
  b=indicators(RAW,CUT);_,signals=scan(b);s=signals[0];i=s['c2_index']-2
  altered=[dict(x) for x in b[:i+4]]
  altered[i+1]['time']+=60
  c,ss=scan(altered);bad=next(x for x in c if x['id']==s['id']);self.assertEqual(bad['state'],'Rejected');self.assertIn('missing-hour gap',bad['reason']);self.assertNotIn(s['id'],[x['id'] for x in ss])
  altered=[dict(x) for x in b[:i+4]];altered[i+1]['ema10']=altered[i]['ema10']
  c,ss=scan(altered);self.assertEqual(next(x for x in c if x['id']==s['id'])['state'],'Rejected');self.assertNotIn(s['id'],[x['id'] for x in ss])
 def test_refresh_dedup_and_candidate_separation(self):
  a=build(RAW,CUT);b=build(RAW,CUT);ids=[s['id'] for s in a['signals']];self.assertEqual(len(ids),len(set(ids)));self.assertEqual(ids,[s['id'] for s in b['signals']]);self.assertEqual(a['signals'][0]['decision_time'],'2026-10-01 20:00:00');self.assertGreater(len(a['candidates']),len(a['signals']))
 def test_tick_touch(self):
  d=build(RAW,CUT);s=d['signals'][-1];p=d['candles'][-1];level=touch_level(p)
  self.assertIsNone(observe(s,p,p['time']+3600,CUT,level+1,level+1.01))
  event=observe(s,p,CUT,CUT,level-.01,level)
  self.assertEqual(event['status'],'Touch observed');self.assertEqual(event['price_kind'],'Observed bid reference — not executed')
if __name__=='__main__':unittest.main()
