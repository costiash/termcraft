---
name: harness
description: Entry point — `/termcraft:harness <path-to-dir-or-script | audit <existing harness>>` hands the job to the harness-architect agent, which digests the source, models the process as stages, generates a guided resumable CLI harness with a TUI theme, and verifies it in a pty — or audits and fixes an existing harness. Use when the user invokes the command or asks for an installer/operator CLI/wizard for a codebase, or to test, evaluate and improve an existing one.
---

# /termcraft:harness

Delegate the whole job to `termcraft:harness-architect` using the Agent tool. Pass the user's request verbatim plus known context (paths, processes, audience, existing harness, reachable infrastructure, operator's terminal). Wait for the result, not merely a spawn acknowledgement, before claiming completion.

The architect digests, models and generates the harness (or audits it), delegates the look to `termcraft:tui-designer`, and verifies in a pty. If it returns theme candidates awaiting a choice, present them in the user-facing conversation and resume the architect with the user's choice; if resume is unavailable, dispatch it again with the prior artifact paths and choice. Wait for the final files and verification summary; relay both without redoing the work.

Nested agents are supported up to depth 3, subject to host tools and policy. If a spawn is unavailable or rejected, do not recurse or bypass the restriction: read `${CLAUDE_PLUGIN_ROOT}/skills/cli-harness/SKILL.md` and follow the workflow inline using available, permitted tools. Report any remaining capability gap to the parent/user rather than claiming unperformed verification.

Arguments: `$ARGUMENTS`. Examples:

- `/termcraft:harness ~/code/promoter-brain-core` — build the operator harness for the repo
- `/termcraft:harness ./install.sh` — wrap the flow this script starts
- `/termcraft:harness audit tools/installer` — explore, evaluate and fix the existing wizard

If the user already selected a theme or explicitly delegated the choice, carry that authorization through each agent handoff and proceed without asking again. Persist candidate paths, selection and verification artifacts before returning control to a parent.
