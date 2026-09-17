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
