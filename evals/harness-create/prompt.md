---
name: harness-create
---

The workspace contains `relay/`, a small service whose only setup path is `relay/install.sh`. Build an operator CLI harness for it: model install → configure → migrate → ready as stages with real preconditions, make it resumable and safe to re-run, generate it on the plugin's harness kit, give it a terminal look (pick the family default yourself — I'm not here to choose), and verify it in a pty before you hand it back. Put everything under `relay/harness/`.
