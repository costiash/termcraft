"""Runtime truthfulness and cleanup regressions."""
import contextlib
import io
import signal
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import harness_kit as k
from test_kit import run

class RuntimeReview(unittest.TestCase):
    def test_unknown_result_stops_dependents(self):
        with tempfile.TemporaryDirectory() as d:
            effects = []
            stages = [k.Stage('a','a',lambda c:k.Verdict('unknown'),lambda c:None),
                      k.Stage('b','b',lambda c:k.Verdict('todo'),lambda c:effects.append('b'),needs=['a'])]
            code, output, journal = run('unknown',stages,['--yes'],Path(d))
            self.assertEqual(code,4)
            self.assertEqual(effects,[])
            self.assertNotIn('all stages done',output)
            self.assertIn('ran-unverified',journal)

    def test_subprocess_failure_is_not_success(self):
        with tempfile.TemporaryDirectory() as d:
            ctx=k.Context(Path(d),{},k.Journal(Path(d)/'j'),k.UI('test'))
            with self.assertRaises(k.subprocess.CalledProcessError):
                ctx.sh([sys.executable,'-c','raise SystemExit(9)'],capture_output=True)

    def test_invalid_verdict_rejected(self):
        with self.assertRaises(ValueError): k.Verdict('typo')

    def test_signal_handler_restored(self):
        with tempfile.TemporaryDirectory() as d, patch.object(k,'TTY',False), contextlib.redirect_stdout(io.StringIO()):
            before=signal.getsignal(signal.SIGINT)
            try:
                k.Harness('test',[],Path(d),k.UI('test')).main(['--check'])
                self.assertIs(signal.getsignal(signal.SIGINT),before)
            finally: signal.signal(signal.SIGINT,before)

    def test_ascii_applies_to_plan_and_panels(self):
        with patch.object(k,'UNICODE',False),patch.object(k,'TTY',False),patch.object(k,'RICH',None),contextlib.redirect_stdout(io.StringIO()) as out:
            ui=k.UI('test')
            ui.panel('Résumé',['→ café'])
            ui.plan([('*','Résumé','todo','→ café')])
        self.assertTrue(out.getvalue().isascii())

    def test_version_probe_fails_closed_and_reads_stderr(self):
        from subprocess import CompletedProcess
        with patch.object(k, 'which', return_value='/bin/tool'):
            for result, expected in [(CompletedProcess([],1,'1.9',''),'unknown'),
                                     (CompletedProcess([],0,'unparseable',''),'unknown'),
                                     (CompletedProcess([],0,'','tool 1.9'),'blocked')]:
                with patch.object(k.subprocess,'run',return_value=result):
                    self.assertEqual(k.probe_command('tool','upgrade',['--version'],(2,0)).status,expected)

    def test_eof_cannot_bypass_default_validation(self):
        with patch.object(k,'RICH',None),patch('builtins.input',side_effect=EOFError):
            q=k.Question('q','q',default='invalid',validate=lambda v:'bad')
            self.assertIsNone(k.UI('test')._ask_loop(q))

if __name__=='__main__': unittest.main()
