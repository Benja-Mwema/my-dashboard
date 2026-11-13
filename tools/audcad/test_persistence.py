import unittest,tempfile,sqlite3
from pathlib import Path
from engine import *
from refresh_audcad import persist
class Persistence(unittest.TestCase):
 def test_restart_and_late_detection(self):
  with tempfile.TemporaryDirectory() as td:
   raw=read_csv(Path(__file__).parent/'source/audcad/AUDCAD_M30_raw_warmup.csv');cut=epoch('2026-11-12 22:00:00');d=build(raw,cut);d.update(source_revision='fixture',rule_config_hash='frozen')
   path=Path(td)/'state.db';persist(d,path,'first-capture',cut);persist(d,path,'second-capture',cut+900)
   c=sqlite3.connect(path);self.assertEqual(c.execute('SELECT count(*) FROM signals').fetchone()[0],120);self.assertEqual(c.execute('SELECT count(DISTINCT first_detected) FROM signals').fetchone()[0],1);self.assertEqual(c.execute('SELECT first_detected FROM signals LIMIT 1').fetchone()[0],'first-capture');c.close()
   self.assertTrue(all(e['discovery']=='Historical / late discovery' for e in d['entries']))
if __name__=='__main__':unittest.main()
