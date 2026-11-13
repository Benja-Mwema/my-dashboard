import unittest,json,csv,hashlib
from pathlib import Path
from engine import *
ROOT=Path(__file__).parent;SOURCE=ROOT/'source';RAW=read_csv(SOURCE/'audcad/AUDCAD_M30_raw_warmup.csv');CUT=epoch('2026-11-12 22:00:00')
class Tests(unittest.TestCase):
 def test_hashes(self):
  for f,h in json.loads((SOURCE/'SHA256SUMS.json').read_text()).items():self.assertEqual(hashlib.sha256((SOURCE/f).read_bytes()).hexdigest(),h)
 def test_fixtures(self):
  d=build(RAW,CUT)
  for side,file in [('BUY','buy_jannov_v0_1/all_cases.csv'),('SELL','jannov_research/classified_cases.csv')]:
   with (SOURCE/'audcad'/file).open() as f:expected=list(csv.DictReader(f))
   got=[e for e in d['entries'] if e['direction']==side and e['entry_price'] is not None];self.assertEqual(len(got),len(expected))
   for e,z in zip(got,expected):
    for k in ('entry_time',):self.assertEqual(e[k],z[k])
    self.assertEqual(e['signal_bar_open'],z['signal_bar'])
    for k in ('entry_price','tp_price','sl_price','highest_pips'):self.assertAlmostEqual(e[k],float(z[k]),8,msg=e['id']+' '+k)
    self.assertEqual(e['execution_status'],{'WIN':'TP60','LOSS':'SL60','OPEN':'OPEN'}[z['outcome']]);self.assertEqual(e['exit_bar_open'] or '',z['exit_bar'])
   print(side,d['summaries'][side])
  unscored=[e for e in d['entries'] if e['execution_status']=='UNSCORED'];self.assertEqual(len(unscored),1);self.assertEqual(unscored[0]['entry_time'],'2026-04-18 00:00:00')
 def test_prefix_and_incomplete(self):
  d=build(RAW,CUT)
  for e in d['entries']:
   t=epoch(e['signal_available_at']);pre=candles(RAW,t-1);self.assertNotIn(e['signal_bar_open'],[b['open_time'] for b in pre]);part=candles(RAW,t);self.assertEqual(part[-1]['macd_signal'],e['indicator_snapshot']['macd_signal']);self.assertTrue(qualifies(part[-1],part[-2],e['sgn']))
 def test_integrity_and_pairs(self):
  with self.assertRaises(ValueError):candles([RAW[0],RAW[0]],CUT)
  self.assertEqual(len(candles(RAW[:1],CUT)),0)
  self.assertEqual(len(candles(RAW[:2],RAW[1]['time']+1799)),0)
 def test_barriers_and_movement(self):
  t=epoch('2026-01-01');bar=lambda h,l:dict(time=t,open=1.,high=h,low=l,close=1.)
  self.assertEqual(outcome(1.,[bar(1.007,.993)],t+1800,1)['execution_status'],'AMBIGUOUS')
  self.assertFalse(outcome(1.,[bar(1.002,.999)],t+1800,1)['movement_success'])
  x=outcome(1.,[bar(1.00201,.999)],t+1800,1);self.assertTrue(x['movement_success']);self.assertAlmostEqual(x['sl_price'],.994)
  self.assertEqual(outcome(1.,[bar(1.006,1.)],t+1800,1)['execution_status'],'TP60')
  self.assertEqual(outcome(1.003,[bar(1.006,1.)],t+1800,1)['execution_status'],'OPEN')
 def test_dedup_overlap(self):
  a=build(RAW,CUT);b=build(RAW,CUT);self.assertEqual([e['id'] for e in a['entries']],[e['id'] for e in b['entries']]);self.assertEqual(len(a['entries']),len({e['id'] for e in a['entries']}));self.assertTrue(any(e['overlapping_entry_ids'] for e in a['entries']))
if __name__=='__main__':unittest.main()
