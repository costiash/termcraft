---
name: design-theme-pick
description: A theme request for an ops CLI must go through the theme bank, show candidates with fallbacks, and not hand-pick colours.
tags: [smoke, design]
runs: 1
max_turns: 25
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Agent]
expected_outcome: Names 2–3 bank themes (noir/slate/blueprint for an ops tool) as candidates, explains the mono/ASCII/light-terminal variants, offers make_theme.py generation, invents no hex values.
---

Our operator CLI `pb` (an ops/data pipeline installer, run on dark truecolor terminals, sometimes piped into CI logs) prints plain text today. Give it a proper terminal look: propose theme candidates I can choose from and tell me what CI / NO_COLOR users will see. Don't apply anything yet — I want to pick first.
