import unittest
from refresh_audcad import safe_cutoff
from engine import candles,outcome
class Completion(unittest.TestCase):
 def test_stale_position_zero_is_never_completed(self):
  bars=[{'time':0,'open':1.,'high':1.001,'low':.999,'close':1.},{'time':1800,'open':1.,'high':1.001,'low':.999,'close':1.}]
  cutoff=safe_cutoff(bars,7200);self.assertEqual(cutoff,1800);self.assertEqual(candles(bars,cutoff),[])
 def test_partial_exit_is_not_final(self):
  b={'time':3600,'open':1.,'high':1.007,'low':.999,'close':1.006}
  self.assertEqual(outcome(1.,[b],5399,1)['execution_status'],'OPEN');self.assertEqual(outcome(1.,[b],5400,1)['execution_status'],'TP60')
if __name__=='__main__':unittest.main()
