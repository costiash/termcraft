import tempfile
import unittest
from pathlib import Path
import digest

class DigestContract(unittest.TestCase):
    def test_local_imports_and_scoped_scripts(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'pyproject.toml').write_text('[project]\nname="sample"\n[project.scripts]\nrun="widget.cli:main"\n[tool.other]\nfake="other:main"\n')
            (root/'widget').mkdir()
            (root/'widget/__init__.py').write_text('')
            (root/'widget/cli.py').write_text('from widget import helper\n')
            result=digest.digest(root)
            self.assertEqual([e['name'] for e in result['entrypoints'] if e['kind']=='console_script'],['run'])
            self.assertIn('widget',result['imports']['sample'])

    def test_missing_root_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError): digest.digest(Path(d)/'missing')

    def test_mermaid_ids_and_escaping(self):
        self.assertNotEqual(digest._id('a-b'),digest._id('a_b'))
        result=digest.mermaid({'exec_chain':{'a.sh':['echo "hello"\nnext']},'imports':{},'entrypoints':[]})
        self.assertNotIn('echo "hello"',result)
        self.assertNotIn('\nnext',result)

if __name__=='__main__': unittest.main()
