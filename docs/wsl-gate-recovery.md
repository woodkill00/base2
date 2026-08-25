# WSL exact-gate recovery

`scripts/run-complete-gate-wsl.ps1` is the Windows-side entry point for a complete gate when the WSL Python runtime is unstable. It requires committed tracked changes, captures the exact source commit, and runs the unchanged repository gate inside WSL.

If the gate fails, the classifier inspects integrity-bound check logs. A restart is allowed only when every failed check contains a narrowly recognized native-corruption signature: a Python segmentation fault, allocator corruption, or Playwright's exact unexpected worker `SIGSEGV` result. Any screenshot mismatch, accessibility assertion, product assertion, security, coverage, build, policy, or mixed failure is returned immediately without restart. At most one WSL shutdown/restart is allowed, and the exact commit must remain unchanged before replay. A second native failure remains a failure and requires operator investigation.

This mechanism does not turn a failed gate green, skip checks, increase application retries, mutate source, or broaden deployment authority. Both the original failed evidence and replacement run remain preserved.
