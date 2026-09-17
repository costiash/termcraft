#!/usr/bin/env python3
"""test_kit.py — contract tests for harness_kit (stdlib unittest). Run: python3 test_kit.py

These encode the findings of the 2026-09-17 external review of v0.5.0 so they cannot come back:
dry-run must not execute; every answer source is validated; unknown probes are not "done"; secrets
declared on a Question are redacted everywhere; non-TTY without --yes does not execute; --from skips;
stages are re-probed before running; a stage blocked only by a pending predecessor waits instead of
blocking the plan; --check is read-only and reruns are idempotent.
"""
import contextlib, io, json, os, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_kit as k


def run(name, stages, args, root):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), patch.object(k, "TTY", False), patch.object(k, "RICH", None):
        previous_sigint = k.signal.getsignal(k.signal.SIGINT)
        try:
            h = k.Harness(name, stages, root, k.UI(name)); rc = h.main(args)
        finally:
            k.signal.signal(k.signal.SIGINT, previous_sigint)
    j = h.journal.path.read_text() if h.journal.path.exists() else ""
    return rc, out.getvalue(), j


class KitContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()

    def test_dry_run_never_calls_run(self):
        marker = self.root / "m"
        st = [k.Stage("w", "w", lambda c: k.Verdict("todo"), lambda c: marker.write_text("x"), describe=lambda c: ["would write m"])]
        rc, out, _ = run("dry", st, ["--dry-run", "--yes"], self.root)
        self.assertEqual(rc, 0); self.assertFalse(marker.exists()); self.assertIn("would write m", out); self.assertIn("nothing was changed", out)

    def test_ctx_sh_refuses_in_dry_run(self):
        st = [k.Stage("w", "w", lambda c: k.Verdict("todo"), lambda c: c.sh(["true"]))]
        rc, out, _ = run("drysh", st, ["--dry-run", "--yes"], self.root)
        self.assertEqual(rc, 0); self.assertIn("no describe() declared", out)

    def test_validation_applies_to_every_source(self):
        for source in ("arg", "env", "default", "fact"):
            seen = []
            q = k.Question("port", "Port", default="bad" if source == "default" else None, env="KIT_TEST_PORT", validate=lambda s: None if s.isdigit() else "digits only")
            os.environ.pop("KIT_TEST_PORT", None)
            if source == "env": os.environ["KIT_TEST_PORT"] = "bad"
            probe = lambda c, s=source: k.Verdict("done" if seen else "todo", facts={"port": "bad"} if s == "fact" else {})
            st = [k.Stage("s", "s", probe, lambda c: seen.append(c.answers["port"]), ask=[q])]
            rc, out, _ = run("val" + source, st, ["--yes"] + (["--answer", "port=bad"] if source == "arg" else []), self.root)
            self.assertEqual(rc, 6, source); self.assertEqual(seen, [], source); self.assertIn("digits only", out)
        os.environ.pop("KIT_TEST_PORT", None)

    def test_unknown_probe_is_not_done(self):
        st = [k.Stage("s", "s", lambda c: k.Verdict("unknown", "cannot verify"), lambda c: None)]
        rc, out, j = run("unk", st, ["--yes"], self.root)
        self.assertEqual(rc, 4); self.assertNotIn('"event": "done"', j); self.assertIn("ran-unverified", j); self.assertIn("cannot confirm", out)

    def test_declared_secret_redacted_in_stdout_journal_and_dry_run(self):
        secret = "SYNTHETIC_TOKEN_123"
        def fail(c): raise RuntimeError("bad credential " + c.answers["token"])
        st = [k.Stage("s", "s", lambda c: k.Verdict("todo"), fail, ask=[k.Question("token", "token", secret=True)])]
        rc, out, j = run("sec", st, ["--yes", "--answer", "token=" + secret], self.root)
        self.assertEqual(rc, 4); self.assertNotIn(secret, out); self.assertNotIn(secret, j); self.assertIn("shell history", out)
        st = [k.Stage("s", "s", lambda c: k.Verdict("todo"), lambda c: None, describe=lambda c: [c.would(["echo", c.answers["pw"]])], ask=[k.Question("pw", "pw", secret=True)])]
        rc, out, _ = run("drysec", st, ["--dry-run", "--yes", "--answer", "pw=" + secret], self.root)
        self.assertEqual(rc, 0); self.assertNotIn(secret, out); self.assertIn("[redacted]", out)

    def test_non_tty_without_yes_does_not_execute(self):
        seen = []
        st = [k.Stage("s", "s", lambda c: k.Verdict("done" if seen else "todo"), lambda c: seen.append("ran"))]
        rc, out, _ = run("ntty", st, [], self.root)          # unittest runs without a TTY
        self.assertEqual(rc, 6); self.assertEqual(seen, []); self.assertIn("--yes", out)

    def test_from_skips_earlier_stages(self):
        seen = []
        st = [k.Stage(x, x, lambda c, x=x: k.Verdict("done" if x in seen else "todo"), lambda c, x=x: seen.append(x)) for x in ("a", "b")]
        rc, _, _ = run("from", st, ["--yes", "--from", "b"], self.root)
        self.assertEqual(rc, 0); self.assertEqual(seen, ["b"])

    def test_from_does_not_probe_earlier_stages(self):
        probes = []
        effects = []
        def early(ctx):
            probes.append("a")
            return k.Verdict("blocked", "must not be consulted", facts={"early": "leaked"})
        def selected(ctx):
            probes.append("b")
            self.assertNotIn("early", ctx.answers)
            return k.Verdict("done" if effects else "todo")
        stages = [k.Stage("a", "a", early),
                  k.Stage("b", "b", selected, lambda ctx: effects.append("b"), needs=["a"])]
        rc, out, _ = run("from-probes", stages, ["--yes", "--from", "b"], self.root)
        self.assertEqual(rc, 0)
        self.assertNotIn("a", probes)
        self.assertEqual(probes, ["b", "b", "b"])
        self.assertEqual(effects, ["b"])
        self.assertIn("skip", out)

    def test_reprobe_before_run_skips_work_done_by_predecessor(self):
        seen = []
        probe = lambda c: k.Verdict("done" if seen else "todo")
        st = [k.Stage("a", "a", probe, lambda c: seen.extend(["a", "b"])), k.Stage("b", "b", probe, lambda c: seen.append("dup"), needs=["a"])]
        rc, out, _ = run("reprobe", st, ["--yes"], self.root)
        self.assertEqual(rc, 0); self.assertEqual(seen, ["a", "b"]); self.assertIn("already done", out)

    def test_blocked_by_pending_predecessor_waits(self):
        seen = []
        st = [k.Stage("install", "install", lambda c: k.Verdict("done" if seen else "todo"), lambda c: seen.append("installed")),
              k.Stage("dep", "dep", lambda c: k.Verdict("done" if seen else "blocked", "missing dependency"), needs=["install"])]
        rc, out, _ = run("wait", st, ["--yes"], self.root)
        self.assertEqual(rc, 0); self.assertEqual(seen, ["installed"]); self.assertIn("waiting", out)

    def test_unknown_readonly_stage_waiting_on_predecessor_does_not_block(self):
        seen = []
        st = [k.Stage("setup", "setup", lambda c: k.Verdict("done" if seen else "todo"), lambda c: seen.append("ran")),
              k.Stage("health", "health", lambda c: k.Verdict("done", "ok") if seen else k.Verdict("unknown", "waiting for setup"), needs=["setup"])]
        rc, out, _ = run("unkwait", st, ["--yes"], self.root)
        self.assertEqual(rc, 0); self.assertEqual(seen, ["ran"]); self.assertIn("waiting", out); self.assertIn("all stages done", out)

    def test_unknown_readonly_prerequisite_without_pending_needs_blocks(self):
        st = [k.Stage("gpu", "gpu", lambda c: k.Verdict("unknown", "cannot tell")), k.Stage("s", "s", lambda c: k.Verdict("todo"), lambda c: None, needs=["gpu"])]
        rc, out, _ = run("unkblk", st, ["--yes"], self.root)
        self.assertEqual(rc, 3)

    def test_real_precondition_still_blocks(self):
        st = [k.Stage("tool", "tool", lambda c: k.Verdict("blocked", "no docker", "install docker")), k.Stage("s", "s", lambda c: k.Verdict("todo"), lambda c: None, needs=["tool"])]
        rc, out, _ = run("blk", st, ["--yes"], self.root)
        self.assertEqual(rc, 3); self.assertIn("install docker", out)

    def test_check_is_read_only_and_rerun_idempotent(self):
        seen = []
        st = [k.Stage("s", "s", lambda c: k.Verdict("done" if seen else "todo"), lambda c: seen.append("ran"))]
        self.assertEqual(run("pos", st, ["--check"], self.root)[0], 0); self.assertEqual(seen, [])
        self.assertEqual(run("pos", st, ["--yes"], self.root)[0], 0)
        rc, out, _ = run("pos", st, ["--yes"], self.root)
        self.assertEqual(rc, 0); self.assertEqual(seen, ["ran"]); self.assertIn("nothing to do", out)

    def test_invalid_graphs_raise_actionable_errors(self):
        probe = lambda c: k.Verdict("todo")
        cases = [([k.Stage("a", "a", probe), k.Stage("a", "a", probe)], "duplicate"),
                 ([k.Stage("a", "a", probe, needs=["missing"])], "missing"),
                 ([k.Stage("a", "a", probe, needs=["b"]), k.Stage("b", "b", probe, needs=["a"])], "cycle")]
        for stages, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                k.Harness("bad", stages, self.root, k.UI("bad"))

    def test_late_block_after_effect_is_stage_failure(self):
        effects = []
        stages = [k.Stage("a", "a", lambda c: k.Verdict("done" if effects else "todo"), lambda c: effects.append("a")),
                  k.Stage("b", "b", lambda c: k.Verdict("blocked", "unavailable", "retry later"), needs=["a"])]
        rc, out, journal = run("late", stages, ["--yes"], self.root)
        self.assertEqual(rc, k.EXIT_STAGE_FAILED)
        self.assertEqual(effects, ["a"])
        self.assertIn("retry later", out)
        self.assertIn('"event": "blocked"', journal)

    def test_waiting_propagates_through_dependency_chain(self):
        effects = []
        stages = [k.Stage("a", "a", lambda c: k.Verdict("done" if effects else "todo"), lambda c: effects.append("a"))]
        for name, predecessor in (("b", "a"), ("c", "b")):
            stages.append(k.Stage(name, name, lambda c: k.Verdict("done" if effects else "blocked"), needs=[predecessor]))
        self.assertEqual(run("chain", stages, ["--yes"], self.root)[0], 0)
        self.assertEqual(effects, ["a"])

    def test_short_secret_is_redacted_from_plan_and_validation(self):
        secret = "QZ"
        q = k.Question("credential", "Credential", secret=True, validate=lambda value: "invalid " + value)
        stages = [k.Stage("a", "a", lambda c: k.Verdict("todo", "received " + secret), ask=[q])]
        rc, out, journal = run("short", stages, ["--yes", "--answer", "credential=" + secret], self.root)
        self.assertEqual(rc, 6)
        self.assertNotIn(secret, out + journal)

    def test_did_you_mean(self):
        st = [k.Stage("setup", "setup", lambda c: k.Verdict("todo"), lambda c: None)]
        with self.assertRaises(SystemExit) as cm:
            run("dym", st, ["--only", "setpu"], self.root)
        self.assertEqual(cm.exception.code, 2)


class JournalFaults(unittest.TestCase):
    """Journal I/O failures must never escape main(): they degrade to a warning and keep the exit-code contract."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        (self.root / "notadir").write_text("x")                       # a regular file where the journal's parent dir should be → mkdir fails
        self.bad = self.root / "notadir" / "j.jsonl"
    def tearDown(self): self.tmp.cleanup()

    def _run(self, stages, args, journal=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), patch.object(k, "TTY", False), patch.object(k, "RICH", None):
            h = k.Harness("jf", stages, self.root, k.UI("jf"), journal_path=journal); rc = h.main(args)
        return rc, out.getvalue(), h

    def test_unwritable_before_any_effect_exits_3_and_runs_nothing(self):
        seen = []
        st = [k.Stage("s", "s", lambda c: k.Verdict("done" if seen else "todo"), lambda c: seen.append("ran"))]
        rc, out, h = self._run(st, ["--yes"], journal=self.bad)
        self.assertEqual(rc, 3); self.assertEqual(seen, []); self.assertIn("journal unwritable", out); self.assertIn("nothing was changed", out)
        self.assertTrue(h.journal.broken); self.assertNotIn("Traceback", out)

    def test_unwritable_after_effects_started_exits_4_without_running_more(self):
        seen = []
        def first(c): seen.append("a"); c.journal.path = self.bad; c.journal.broken = None   # journal breaks after stage a ran
        st = [k.Stage("a", "a", lambda c: k.Verdict("done" if "a" in seen else "todo"), first),
              k.Stage("b", "b", lambda c: k.Verdict("done" if "b" in seen else "todo"), lambda c: seen.append("b"), needs=["a"])]
        rc, out, _ = self._run(st, ["--yes"])
        self.assertEqual(rc, 4); self.assertEqual(seen, ["a"]); self.assertIn("earlier stages ran", out); self.assertRegex(out, r"rerun\s+resumes")

    def test_done_event_unwritable_keeps_exit_0_and_warns(self):
        seen = []
        def run(c): seen.append("ran"); c.journal.path = self.bad; c.journal.broken = None
        st = [k.Stage("s", "s", lambda c: k.Verdict("done" if seen else "todo"), run)]
        rc, out, _ = self._run(st, ["--yes"])
        self.assertEqual(rc, 0); self.assertIn("all stages done", out); self.assertIn("journal unwritable", out)

    def test_failed_event_unwritable_keeps_original_error_and_exit_4(self):
        def run(c): c.journal.path = self.bad; c.journal.broken = None; raise RuntimeError("the real cause")
        st = [k.Stage("s", "s", lambda c: k.Verdict("todo"), run)]
        rc, out, _ = self._run(st, ["--yes"])
        self.assertEqual(rc, 4); self.assertIn("the real cause", out); self.assertIn("journal unwritable", out)

    def test_unreadable_journal_at_construction_warns_and_continues(self):
        d = self.root / "ro"; d.mkdir(); j = d / "j.jsonl"; j.write_text('{"stage":"s","event":"done"}\n'); j.chmod(0)
        try:
            if os.geteuid() == 0: self.skipTest("root ignores file modes")
            seen = []
            st = [k.Stage("s", "s", lambda c: k.Verdict("done" if seen else "todo"), lambda c: seen.append("ran"))]
            rc, out, h = self._run(st, ["--check"], journal=j)
            self.assertEqual(rc, 0); self.assertIn("journal unreadable", out); self.assertEqual(h.journal.events, [])
        finally: j.chmod(0o600)

    def test_journal_flag_overrides_location(self):
        seen = []; j = self.root / "elsewhere" / "run.jsonl"
        st = [k.Stage("s", "s", lambda c: k.Verdict("done" if seen else "todo"), lambda c: seen.append("ran"))]
        rc, _, _ = self._run(st, ["--yes", "--journal", str(j)])
        self.assertEqual(rc, 0); self.assertTrue(j.exists()); self.assertIn('"event": "done"', j.read_text())


if __name__ == "__main__":
    unittest.main(verbosity=1)
