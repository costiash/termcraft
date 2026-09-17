"""Synthetic end-to-end PTY matrix using the shipped generators and runtime."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from drive_harness import run_scenario

HERE=Path(__file__).resolve().parent
TUI=HERE.parent.parent/'tui-design/scripts'
FIXTURE='''from pathlib import Path
import os, sys, time
sys.path.insert(0, {kit!r})
from harness_kit import *
try:
    from theme import THEME, BANNER
except ModuleNotFoundError as exc:
    if exc.name != 'theme': raise
    THEME, BANNER = None, None
root=Path(__file__).parent
marker=root/'state'
def probe(c):
    return Verdict('blocked', 'synthetic block', 'unset BLOCK') if os.getenv('BLOCK') else Verdict('done' if marker.exists() else 'todo')
def effect(c):
    if os.getenv('WAIT'):
        print('effect waiting',flush=True)
        time.sleep(5)
    c.sh([sys.executable,'-c','raise SystemExit(9 if '+repr(bool(os.getenv('FAIL')))+' else 0)'])
    marker.write_text('done')
stage=Stage('setup','setup [literal]',probe,effect,
    ask=[Question('credential','Synthetic credential',secret=True,env='SYNTHETIC_CREDENTIAL',validate=lambda s: None if s else 'required')],
    describe=lambda c:['would write state'])
raise SystemExit(Harness('demo',[stage],root,UI('demo',theme=THEME,banner=BANNER)).main())
'''

class Integration(unittest.TestCase):
    def test_pty_matrix(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); program=root/'demo.py'
            program.write_text(FIXTURE.format(kit=str(HERE)))
            subprocess.run([sys.executable,str(TUI/'make_theme.py'),'--name','DEMO','--out',str(root/'theme.py')],check=True,capture_output=True)
            cases=[
                ('check',['--check'],{},0,[]),
                ('dry',['--dry-run','--yes'],{},0,[]),
                ('blocked',['--yes'],{'BLOCK':'1'},3,[]),
                ('missing',['--yes'],{'SYNTHETIC_CREDENTIAL':''},6,[]),
                ('fail',['--yes'],{'FAIL':'1'},4,[]),
                ('ctrl-c',['--yes'],{'WAIT':'1'},5,[{'expect':'effect waiting','send':'\\x03'}]),
                ('interactive',[],{'SYNTHETIC_CREDENTIAL':''},0,[{'expect':'Synthetic credential:', 'send':'SYNTHETIC_TEST\\n', 'secret':'SYNTHETIC_TEST'}, {'expect':'proceed', 'send':'y\\n'}]),
                ('plain',['--yes'],{'HARNESS_PLAIN':'1'},0,[]),
                ('rerun',['--yes'],{},0,[]),
                ('ascii',['--yes'],{'HARNESS_ASCII':'1'},0,[]),
                ('mono',['--yes'],{'NO_COLOR':''},0,[]),
                ('light',['--yes'],{'HARNESS_BG':'light'},0,[]),
                ('rich',['--yes'],{'HARNESS_PLAIN':''},0,[]),
            ]
            for name,args,env,code,script in cases:
                if name not in ('rerun',): (root/'state').unlink(missing_ok=True)
                if name=='missing': (root/'theme.py').unlink()  # optional-theme fallback
                sc={'name':name,'cmd':[sys.executable,str(program),*args], 'cwd':d,'cols':80,'timeout':3,
                    'env':{'TERM':'xterm-256color','NO_COLOR':'1','HARNESS_PLAIN':'1','SYNTHETIC_CREDENTIAL':'SYNTHETIC_TEST',**env},
                    'script':script,'assert':{'exit_code':code,'stdout_not_matches':['Traceback','SYNTHETIC_TEST']}}
                if name=='rich':
                    # Driver inherits env; use a separate wrapper to remove NO_COLOR before import.
                    sc['cmd']=[sys.executable,'-c','import os,runpy,sys; os.environ.pop("NO_COLOR",None); sys.argv='+repr([str(program),*args])+'; runpy.run_path('+repr(str(program))+',run_name="__main__")']
                result=run_scenario(sc,root/'transcripts')
                self.assertEqual(result['fails'],[],name)
                if name in ('check','dry','blocked','missing','fail','ctrl-c'):
                    self.assertFalse((root/'state').exists(),name)
                journal=root/'.harness/demo.jsonl'
                if journal.exists(): self.assertNotIn('SYNTHETIC_TEST',journal.read_text())
            cp=subprocess.run([sys.executable,str(program),'--yes'],env={**os.environ,'SYNTHETIC_CREDENTIAL':'SYNTHETIC_TEST'},capture_output=True,text=True,timeout=3)
            self.assertEqual(cp.returncode,0)
            self.assertNotIn('\x1b',cp.stdout)

if __name__=='__main__': unittest.main()
