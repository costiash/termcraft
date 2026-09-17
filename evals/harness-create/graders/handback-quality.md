---
type: llm
focus: last_message
---

PASS if the final reply lists the harness's stages (at least: a host/python precondition, venv or dependency install, config/token, migrate), states the exit-code contract or how a blocked precondition versus a failure after effects is reported, says how a rerun resumes, and names what was verified in a pty (scenarios run, dry-run/check changing nothing, secrets absent from output) with the theme that was applied.
FAIL if it claims completion without saying what was run, if the harness re-implements install steps instead of delegating to the project's own commands, or if it asks the user to choose a theme despite being told to pick the default.
