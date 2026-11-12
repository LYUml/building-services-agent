import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from bsa import reference_library as library

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('git'),'requires host Git')
class ReferenceLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.assertTrue(self.root.is_relative_to(ROOT/'runs'))
        self.patch=patch.object(library,'ROOT',self.root);self.patch.start();self.addCleanup(self.patch.stop)
        self.git('init')
        for name,text in [('docs/guide.md','Public reference guide'),('examples/input.json','{"source":"Synthetic reference, not a project fact","value":1}'),('contracts/test.json','{"type":"object"}'),('docs/evidence/hidden.md','Excluded evidence'),('examples/program.py','Excluded program')]:
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8')
        self.commit()

    def git(self,*args):
        return subprocess.run([shutil.which('git'),'-C',str(self.root),*args],capture_output=True,text=True,check=True).stdout.strip()

    def commit(self):
        self.git('add','.');self.git('-c','user.name=Source fixture','-c','user.email=source@example.invalid','commit','-m','Reference fixture')

    def test_committed_content_excludes_untracked_worktree_and_unsupported_files(self):
        (self.root/'examples/untracked.json').write_text('Untracked project data')
        original=(self.root/'examples/input.json').read_bytes();(self.root/'examples/input.json').write_text('Uncommitted project modification')
        result=library.catalogue();self.assertEqual(result['total'],3)
        row=next(r for r in result['references'] if r['path']=='examples/input.json')
        data=library.read(result['revision'],row['id'])
        self.assertEqual(data['content_utf8'].encode('utf-8'),original)
        self.assertEqual(data['sha256'],hashlib.sha256(original).hexdigest())
        self.assertIn('not actual project facts',data['classification'])
        self.assertEqual((self.root/'examples/input.json').read_text(),'Uncommitted project modification')
        with patch.dict(os.environ,{'GIT_DIR':str(self.root/'nonexistent-other-repository'),'GIT_WORK_TREE':str(self.root/'other-worktree')}):
            self.assertEqual(library.catalogue()['revision'],result['revision'])

    def test_old_resource_keeps_exact_commit_after_new_head(self):
        first=library.catalogue('example');row=first['references'][0]
        (self.root/'examples/input.json').write_text('{"value":2}');self.commit()
        second=library.catalogue('example');self.assertNotEqual(first['revision'],second['revision'])
        self.assertNotEqual(library.read(first['revision'],row['id'])['sha256'],library.read(second['revision'],row['id'])['sha256'])

    def test_filters_pagination_and_unlisted_identifiers(self):
        self.assertEqual(library.catalogue('schema')['total'],1)
        first=library.catalogue(limit=1);self.assertEqual(len(first['references']),1);self.assertEqual(first['next_offset'],1)
        self.assertNotEqual(first['references'],library.catalogue(offset=1,limit=1)['references'])
        with self.assertRaises(ValueError):library.read('--untrusted-option','0'*24)
        with self.assertRaises(ValueError):library.read(first['revision'],'../outside')
        with self.assertRaises(ValueError):library.read(first['revision'],'0'*24)
        with self.assertRaises(ValueError):library.catalogue(limit=1000)

    def test_oversized_text_is_listed_but_cannot_be_read(self):
        (self.root/'examples/large.json').write_text('x'*(library.MAX_BYTES+1));self.commit()
        result=library.catalogue(query='large.json');row=result['references'][0]
        self.assertFalse(row['readable'])
        with self.assertRaisesRegex(ValueError,'bounded text size'):library.read(result['revision'],row['id'])


if __name__=='__main__':unittest.main()
