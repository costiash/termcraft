"""Deterministic terminal fallback regressions (no real terminal required)."""
import contextlib
import io
import os
import unittest
from unittest.mock import patch

import harness_kit as k


class TerminalUI(unittest.TestCase):
    def capture(self, callback, width=40, unicode=True):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.multiple(k, TTY=False, RICH=None, MODE="none", UNICODE=unicode), patch.object(k, "cols", return_value=width):
            callback(k.UI("example", banner=["#" * 100]))
        return output.getvalue()

    def test_panel_lines_have_equal_width(self):
        text = self.capture(lambda ui: ui.panel("title", ["short", "long " * 30]))
        self.assertEqual({len(line) for line in text.splitlines()}, {40})

    def test_banner_fits_runtime_width(self):
        text = self.capture(lambda ui: ui.header())
        self.assertLessEqual(max(map(len, text.splitlines())), 40)
        self.assertIn("EXAMPLE", text)

    def test_ascii_messages(self):
        text = self.capture(lambda ui: ui.line("✓ done → next • item ✗ blocked — wait…"), unicode=False)
        self.assertTrue(text.isascii(), text)

    def test_ascii_keeps_meaning_of_comparisons_and_gutters(self):
        # found by the live eval: "python3 ≥ 3.10" became "python3 ? 3.10" and the log gutter │ became ?, the unknown mark
        text = self.capture(lambda ui: ui.line("python3 ≥ 3.10 │ disk ≤ 80% ─ done"), unicode=False)
        self.assertTrue(text.isascii(), text)
        self.assertIn("python3 >= 3.10 | disk <= 80% - done", text)
        self.assertNotIn("?", text)

    def test_plan_title_column_fits_long_titles(self):
        # found by the live create eval: titles were cut at a fixed 28 chars ("python deps (requirements.tx")
        rows = [("•", "python deps (requirements.txt)", "todo", "pip install"), ("✓", "host", "done", "ok")]
        text = self.capture(lambda ui: ui.plan(rows), width=80)
        self.assertIn("python deps (requirements.txt)", text)
        self.assertTrue(all(len(l) <= 80 for l in text.splitlines()), text)

    def test_ascii_terminal_uses_theme_ascii_banner(self):
        class T:
            banner_ascii = ["#### ####", "#    #  #"]
            def roles(self, bg="dark"): return {}
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.multiple(k, TTY=False, RICH=None, MODE="none", UNICODE=False), patch.object(k, "cols", return_value=80):
            k.UI("relay", banner=["████ ╗", "██╔══╝"], theme=T()).header()
        self.assertIn("#### ####", output.getvalue()); self.assertNotIn("RELAY", output.getvalue())

    def test_color_capabilities(self):
        for env, mode in [({"NO_COLOR": "", "TERM": "xterm"}, "none"),
                          ({"TERM": "dumb", "COLORTERM": "truecolor"}, "none"),
                          ({"TERM": "xterm-256color"}, "256")]:
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True), patch.object(k.sys.stdout, "isatty", return_value=True):
                self.assertEqual(k._mode(), mode)

    def test_secret_validation_does_not_echo_rejected_env_value(self):
        output = io.StringIO()
        question = k.Question("credential", "Credential", secret=True, env="TEST_SECRET", validate=lambda value: "invalid " + value)
        with contextlib.redirect_stdout(output), patch.multiple(k, TTY=False, RICH=None, MODE="none"), patch.dict(os.environ, {"TEST_SECRET": "QZ"}):
            self.assertIsNone(k.UI("test").ask(question, unattended=True))
        self.assertNotIn("QZ", output.getvalue())


if __name__ == "__main__":
    unittest.main()
