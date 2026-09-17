# termcraft evals — live acceptance for `claude plugin eval`

Three cases, one per capability. `scripts/check_plugin.py` only checks that these files parse; the live run is
the acceptance gate the static checks cannot replace.

| case | tags | proves | needs |
|---|---|---|---|
| `design-theme-pick` | smoke, design | a theme request reaches the tui-design path and the answer is candidates from the bank with mono/ASCII/light fallbacks, not hand-picked hex | `--allow-tools Bash` (to render previews) |
| `harness-create` | harness, create | an `install.sh` becomes a process model + kit-based harness, and the harness was actually driven in a pty before hand-back | `--scaffold --allow-tools Bash Write Edit` |
| `harness-audit` | harness, audit | an existing interactive installer is explored, its gaps tabled with transcript evidence, and the fixes verified | `--scaffold --allow-tools Bash Write Edit` |

```
# smoke (cheap): one run, single arm, no judge model cost beyond the llm graders
claude plugin eval . --trust-plugin --tag smoke --runs 1 --ablation none --allow-tools Bash --no-publish

# full: both arms, scaffolds on, results under evals/results/<timestamp>/
claude plugin eval . --trust-plugin --scaffold --allow-tools Bash Write Edit --runs 2 --threshold 0.8 \
  --judge-model claude-haiku-4-5 --no-publish --max-cost-usd 15 --json evals/results/last.json
```

Each case sets `runs: 1` so a default invocation stays cheap; raise with `--runs`. Skill/agent `tool_used`
graders are scored in the with-plugin arm only (the CLI does that automatically); regex and llm graders score
both arms, which is what shows the plugin's lift. Read `report.html` for transcripts — a passing score is
necessary, not sufficient.
