#!/usr/bin/env python3
"""test_tools.py — regression tests for ascii_render.py, banner.py, themes.py and the pty driver. Run: python3 test_tools.py
Needs Pillow + numpy for the renderer cases (skipped otherwise). Encodes the 2026-09-17 review findings."""
import json, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
RENDER = HERE / "ascii_render.py"
DRIVE = HERE.parent.parent / "cli-harness" / "scripts" / "drive_harness.py"


class ThemesAndBanners(unittest.TestCase):
    def test_every_theme_has_both_palettes_and_fallbacks(self):
        sys.path.insert(0, str(HERE)); import themes
        for t in themes.THEMES.values():
            for role in ("ink", "dim", "accent", "ok", "warn", "stop"):
                self.assertRegex(t.palette[role], r"^#[0-9a-f]{6}$", t.id); self.assertRegex(t.light[role], r"^#[0-9a-f]{6}$", t.id)
            self.assertIn(t.box, ("light", "rounded", "heavy", "double", "ascii")); self.assertIn(t.banner, ("block", "slab", "shade", "plain"))
            self.assertTrue(t.glyphs.spinner and t.glyphs.meter and set(t.glyphs.marks) >= {"done", "todo", "blocked", "unknown", "waiting"})
            # a glyph must not mean one status on a Unicode terminal and a different status in the ASCII fallback
            # (blueprint's todo "+" collided with the ASCII done "+": found by the live eval)
            ascii_marks = t.glyphs.ascii_fallback["marks"]
            for status, glyph in t.glyphs.marks.items():
                for other, a in ascii_marks.items():
                    if other != status: self.assertNotEqual(glyph, a, f"{t.id}: unicode {status}={glyph!r} equals ascii {other}={a!r}")

    def test_banner_styles_fit_and_fallback(self):
        sys.path.insert(0, str(HERE)); import banner
        for style in ("block", "slab", "shade", "plain"):
            lines = banner.render("PB", style); self.assertTrue(lines); self.assertLessEqual(max(len(l) for l in lines), 80)
        self.assertEqual(banner.fit(banner.render("promoter-brain-core", "block"), 40, "promoter-brain-core"), ["PROMOTER-BRAIN-CORE"])
        self.assertTrue(all(ord(c) < 128 for l in banner.render("PB", "block", ascii_only=True) for c in l))

    def test_make_theme_writes_standalone_file(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "theme.py"
            cp = subprocess.run([sys.executable, str(HERE / "make_theme.py"), "--theme", "paper", "--name", "PB", "--out", str(out)], capture_output=True, text=True)
            self.assertEqual(cp.returncode, 0, cp.stderr)
            cp = subprocess.run([sys.executable, "-c", f"import sys; sys.path.insert(0, {d!r}); from theme import THEME, BANNER; print(THEME.roles('light')['ink'], THEME.box, len(BANNER))"], capture_output=True, text=True)
            self.assertEqual(cp.returncode, 0, cp.stderr); self.assertIn("rounded", cp.stdout)


class Renderer(unittest.TestCase):
    def setUp(self):
        try: from PIL import Image; import numpy  # noqa
        except ImportError: self.skipTest("Pillow/numpy not installed")

    def test_square_stays_square_in_every_style_and_title_is_escaped(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            img = Path(d) / "<b>t.png"; Image.new("RGB", (40, 40), "white").save(img)
            for style in ("characters", "dense", "block", "halfblock", "braille", "dots", "lines"):
                cp = subprocess.run([sys.executable, str(RENDER), str(img), "--cols", "20", "--style", style, "--out", "text"], capture_output=True, text=True)
                self.assertEqual(cp.returncode, 0, style); self.assertEqual(len(cp.stdout.splitlines()), 10, style)   # 20 cols × 1:2 cells → 10 rows
            cp = subprocess.run([sys.executable, str(RENDER), str(img), "--out", "html"], capture_output=True, text=True)
            self.assertIn("<title>&lt;b&gt;t.png</title>", cp.stdout)


class Driver(unittest.TestCase):
    def run_sc(self, sc):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"; p.write_text(json.dumps(sc))
            cp = subprocess.run([sys.executable, str(DRIVE), str(p), "--out", d], capture_output=True, text=True)
            return cp.returncode, cp.stdout

    def test_unicode_send_roundtrips(self):
        rc, out = self.run_sc({"name": "u", "cmd": [sys.executable, "-c", 'print("ready",flush=True);print(input())'], "script": [{"expect": "ready", "send": "שלום\\n"}], "assert": {"exit_code": 0, "stdout_matches": ["שלום"]}})
        self.assertEqual(rc, 0, out)

    def test_timeout_is_a_failure(self):
        rc, out = self.run_sc({"name": "t", "cmd": [sys.executable, "-c", "import time;time.sleep(2)"], "timeout": 0.3})
        self.assertEqual(rc, 1); self.assertIn("timeout", out)


if __name__ == "__main__":
    unittest.main(verbosity=1)
