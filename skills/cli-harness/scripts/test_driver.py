"""Real subprocess regressions; only synthetic secrets, bounded outer waits."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

DRIVER = Path(__file__).with_name('drive_harness.py')

class DriverContract(unittest.TestCase):
    def invoke(self, sc):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'scenario.json'
            p.write_text(json.dumps(sc))
            cp = subprocess.run([sys.executable, str(DRIVER), str(p), '--out', d],
                                capture_output=True, text=True, timeout=4)
            return cp, ''.join(f.read_text() for f in Path(d).glob('*.txt'))

    def test_secret_failure_never_persists_value(self):
        secret = 'SYNTHETIC_LEAK_123'
        cp, transcript = self.invoke({'name':'leak', 'cmd':[sys.executable,'-c',f'print({secret!r})'],
            'script':[{'expect':'never', 'send':'', 'secret':secret}],
            'assert':{'stdout_not_matches':[secret]}})
        self.assertEqual(cp.returncode, 1)
        self.assertNotIn(secret, cp.stdout + cp.stderr + transcript)
        self.assertIn('[redacted]', transcript)

    def test_closed_terminal_still_obeys_timeout(self):
        cp, _ = self.invoke({'name':'closed', 'timeout':0.2, 'cmd':[sys.executable,'-c',
            'import os,time; [os.close(fd) for fd in (0,1,2)]; time.sleep(1)']})
        self.assertEqual(cp.returncode, 1)
        self.assertIn('timeout', cp.stdout)

    def test_same_prompt_cannot_reuse_old_match(self):
        cp, _ = self.invoke({'name':'repeat','timeout':0.2,'cmd':[sys.executable,'-c',
            'import time; print("ready",flush=True); input(); time.sleep(1)'],
            'script':[{'expect':'ready','send':'one\\n'}, {'expect':'ready','send':'two\\n'}]})
        self.assertIn('unmet expect', cp.stdout)

    def test_term_override(self):
        cp, _ = self.invoke({'name':'term','env':{'TERM':'dumb'},'cmd':[sys.executable,'-c',
            'import os; print(os.environ["TERM"])'],'assert':{'stdout_matches':['dumb'], 'exit_code':0}})
        self.assertEqual(cp.returncode, 0, cp.stdout)

    def test_timeout_kills_descendant_in_same_group(self):
        import time
        with tempfile.TemporaryDirectory() as d:
            marker=Path(d)/'survived'
            child='import time; from pathlib import Path; time.sleep(.5); Path('+repr(str(marker))+').write_text("bad")'
            code='import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",'+repr(child)+']); time.sleep(2)'
            cp,_=self.invoke({'name':'descendant','timeout':.15,'cmd':[sys.executable,'-c',code]})
            self.assertEqual(cp.returncode,1)
            time.sleep(.6)
            self.assertFalse(marker.exists())

    def test_unexpected_exit_and_output_limit_fail(self):
        cp,_=self.invoke({'name':'exit','cmd':[sys.executable,'-c','raise SystemExit(9)']})
        self.assertEqual(cp.returncode,1)
        cp,_=self.invoke({'name':'limit','max_output_bytes':128,'cmd':[sys.executable,'-c','print("x"*1000)']})
        self.assertEqual(cp.returncode,1)
        self.assertIn('output limit',cp.stdout)

    def test_empty_directory_fails(self):
        with tempfile.TemporaryDirectory() as d:
            cp = subprocess.run([sys.executable,str(DRIVER),d],capture_output=True,text=True,timeout=4)
        self.assertNotEqual(cp.returncode,0)

if __name__ == '__main__': unittest.main()
