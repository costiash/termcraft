"""Generation, previews and widget boundary regressions."""
import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import banner
import themes
import tui_frame as f
HERE=Path(__file__).resolve().parent

class ToolsReview(unittest.TestCase):
    def test_generated_theme_treats_name_as_data(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'theme.py'
            name='demo"""\nraise RuntimeError("injected")\n#'
            cp=subprocess.run([sys.executable,str(HERE/'make_theme.py'),'--name',name,'--out',str(out)],capture_output=True,text=True)
            self.assertEqual(cp.returncode,0,cp.stderr)
            exec(compile(out.read_text(),str(out),'exec'),{})

    def test_long_plain_banner_fits(self):
        self.assertTrue(all(len(s)<=20 for s in banner.fit(banner.render('x'*100),20,'x'*100)))

    def test_preview_preserves_color_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            cp=subprocess.run([sys.executable,str(HERE/'preview_theme.py'),'--theme','noir','--out',d],capture_output=True,text=True)
            self.assertEqual(cp.returncode,0,cp.stderr)
            ansi=Path(d)/'noir-dark.ansi'
            self.assertTrue(ansi.exists())
            self.assertIn('\x1b[38;2;',ansi.read_text())
            self.assertNotIn('\x1b', (Path(d)/'noir-dark.txt').read_text())

    def test_empty_widgets_and_clamped_meter(self):
        self.assertEqual(f.sparkline([]),'')
        self.assertEqual(f.table([]),[])
        self.assertEqual(f.kv([]),[])
        self.assertEqual(f.columns([],80),[])
        self.assertEqual(len(f.meter(2,10)),10)
        self.assertEqual(len(f.meter(-1,10)),10)

    def test_empty_no_color_and_dumb(self):
        for env in ({'NO_COLOR':''},{'TERM':'dumb'}):
            with patch.dict(os.environ,env,clear=True),patch.object(sys.stdout,'isatty',return_value=True):
                self.assertEqual(f.color_mode(),'none')

    def test_mono_has_no_chromatic_ansi16_roles(self):
        self.assertTrue(all(set(pair)<= {'30','37','90','97'} for pair in themes.THEMES['mono'].ansi16.values()))

    def test_animation_cleanup_on_callback_error(self):
        with patch.dict(os.environ,{'TERM':'xterm'},clear=True),patch.object(sys.stdout,'isatty',return_value=True),patch.object(f,'enter'),patch.object(f,'leave') as leave:
            with self.assertRaises(RuntimeError):
                f.run(lambda *_: (_ for _ in ()).throw(RuntimeError('fail')),duration=.1)
            leave.assert_called()

if __name__=='__main__': unittest.main()
