---
type: llm
focus: last_message
---

PASS if the reply contains a gap table (or equivalent list) in which each finding cites evidence from an actual run (a transcript line, an observed exit code, a file left behind), and the findings include at least three of: the token is echoed in clear text; there is no dry-run or check mode; a failed step still ends with "done" / exit 0; nothing is journaled so a rerun cannot resume; status is conveyed by colour only; the script blocks on input() when not on a TTY. It must also say which fixes were applied and that the fixed script was re-driven.
FAIL if the findings are generic (no evidence from a run), if the wizard was replaced by something operators invoke differently without saying so, or if verification of the fixed version is not mentioned.
