import unittest
from engine import epoch
from exit_overlay import evaluate
T=epoch('2026-01-01')
def bar(i,o,h,l,c):return dict(time=T+i*1800,open=1+o*.0001,high=1+h*.0001,low=1+l*.0001,close=1+c*.0001)
def trade(s=1):return dict(entry_price=1.,entry_time='2026-01-01 00:00:00',sgn=s)
class Overlay(unittest.TestCase):
 def test_strict_half_and_be(self):
  a=bar(0,0,40,0,20);self.assertEqual(evaluate(trade(),[a],T+1800,set())['turns'],[])
  b=bar(1,20,22,15,19);c=bar(2,19,20,-2,0);r=evaluate(trade(),[a,b,c],T+5400,set());self.assertEqual(r['status'],'BE');self.assertEqual(r['gross_pips'],0);self.assertEqual(r['turns'][0]['peak_pips'],40)
 def test_tp_is_closed(self):
  r=evaluate(trade(),[bar(0,0,65,-1,63),bar(1,63,100,62,90)],T+3600,set());self.assertEqual(r['status'],'TP60');self.assertEqual(r['gross_pips'],60)
 def test_early_opposite_vs_sl(self):
  a=bar(0,0,10,-1,4);b=bar(1,4,5,-10,-5)
  self.assertEqual(evaluate(trade(),[a,b],T+3600,{T+1800})['status'],'OPPOSITE')
  self.assertEqual(evaluate(trade(),[a,bar(1,-61,-59,-65,-60)],T+3600,{T+1800})['status'],'SL60')
 def test_uncertainty_and_no_backdate(self):
  self.assertEqual(evaluate(trade(),[bar(0,0,40,-1,-.5)],T+1800,set())['status'],'AMBIGUOUS_BE_ACTIVATION')
  self.assertEqual(evaluate(trade(),[bar(0,0,65,-65,0)],T+1800,set())['status'],'AMBIGUOUS')
 def test_no_partial_turn(self):
  self.assertEqual(evaluate(trade(),[bar(0,0,40,0,10)],T+1799,set())['turns'],[])
 def test_sell_symmetry(self):
  bars=[bar(0,0,0,-40,-19),bar(1,-19,1,-20,0)];r=evaluate(trade(-1),bars,T+3600,set());self.assertEqual(r['status'],'BE')
if __name__=='__main__':unittest.main()
