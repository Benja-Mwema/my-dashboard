import tempfile,unittest,subprocess,json
from pathlib import Path
import refresh_publish as m
class Recovery(unittest.TestCase):
 def test_interrupted_bundle_and_unknown_edits(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);repo=r/'repo';repo.mkdir();m.REPO=repo;m.ROOT=r;m.LOG=r/'log';m.JOURNAL=r/'journal.json'
   subprocess.run(['git','init',str(repo)],capture_output=True,check=True)
   m.git('config','user.name','Test');m.git('config','user.email','test@example.invalid')
   names=['cluster-data.json','gbpjpy-data.json','audcad-data.json']
   for n in names:(repo/n).write_bytes(b'old\n')
   m.git('add','.');m.git('commit','-m','baseline');bak=r/'backup';bak.mkdir()
   for n in names:(bak/n).write_bytes(b'old\n')
   j={'head':m.git('rev-parse','HEAD'),'backup':str(bak),'files':{n:{'old':m.digest(b'old\n'),'new':m.digest(b'new\n')} for n in names}}
   m.JOURNAL.write_text(json.dumps(j));(repo/names[0]).write_bytes(b'new\n');m.recover()
   self.assertEqual((repo/names[0]).read_bytes(),b'old\n');self.assertEqual(m.git('status','--porcelain'),'')
   m.JOURNAL.write_text(json.dumps(j));(repo/names[0]).write_bytes(b'user change\n')
   with self.assertRaises(RuntimeError):m.recover()
   self.assertEqual((repo/names[0]).read_bytes(),b'user change\n')
if __name__=='__main__':unittest.main()
