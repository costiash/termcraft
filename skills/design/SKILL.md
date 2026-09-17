---
name: design
description: >-
  Entry point — `/termcraft:design <request>` hands terminal look-and-feel work to the tui-designer agent: pick a theme for a CLI/TUI/harness from rendered candidates, restyle an existing terminal program, make a banner or splash, render a logo to glyphs. Use when the user invokes the command or asks for a terminal UI to look good, a theme, banner, colour scheme, or retro/CRT/ASCII styling.
---

# /termcraft:design

Delegate to `termcraft:tui-designer` using the Agent tool. Pass the user's request verbatim plus known context (program path, harness name and stages, mood, brand colour, operator's terminal). Wait for its results before relaying previews or claiming completion; a spawn acknowledgement is not a result.

The designer returns candidate paths and recommendations to its parent, not a user question. Present them in the user-facing conversation, obtain the choice, then resume the designer with that choice and its prior context (or dispatch it again with the candidate paths and choice if resume is unavailable). Wait for the final artifacts and verification summary; relay them without redoing the work. Only choose a default when the user has delegated that decision or the run is explicitly unattended, and disclose it.

Nested agents are supported up to depth 3, subject to the host's tools and policy. If spawning is unavailable or rejected, do not retry recursively or bypass the restriction: read `${CLAUDE_PLUGIN_ROOT}/skills/tui-design/SKILL.md` and do the workflow inline with available, permitted tools. If those are insufficient, return the limitation and a handoff to the parent/user.

Arguments: `$ARGUMENTS`. Examples:

- `/termcraft:design theme for the installer in tools/installer — show me noir, slate and blueprint at 80 columns`
- `/termcraft:design restyle ./cli/report.py; it runs on light terminals`
- `/termcraft:design splash screen with assets/logo.png for the pb harness`

If the user already selected a theme or explicitly delegated the choice, carry that authorization through each agent handoff and proceed without asking again. Persist candidate paths, selection and verification artifacts before returning control to a parent.
