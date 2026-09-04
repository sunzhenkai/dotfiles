# Acceptance Evidence — Tasks 8.5–8.6

Date: 2026-09-04 (+08:00)
Change: `harden-dotfiles-state-boundaries`

This appendix records concise acceptance results only. It does not change completion checkboxes in `tasks.md`. All isolated runs used disposable HOME/XDG roots; temporary logs and the synthetic doctor marker were removed on exit.

## Automated gates

| Gate | Command / immutable tool | Result |
|---|---|---|
| Plain full pytest | `python3 -m pytest -q` | PASS — `560 passed, 42 subtests passed in 58.96s` |
| Strict registry/handlers | `python3 scripts/modules.py validate --strict-handlers` | PASS — strict handler validation complete |
| Strict OpenSpec validation | `openspec validate --strict --type change harden-dotfiles-state-boundaries` | PASS — change valid |
| Acceptance contract tests | `python3 -m pytest -q tests/test_ci_contract.py` | PASS — `9 passed` |
| Template check/no delta | `python3 scripts/agents/generate_templates.py --check`, with before/after template diff and content hashes | PASS — `outputs=5`, diff delta none, content delta none |
| First-party ShellCheck | `scripts/ci/shellcheck-first-party.sh` through `koalaman/shellcheck:v0.9.0@sha256:f35e8987b02760d4e76fc99a68ad5c42cc10bb32f3dd2143a3cf92f1e5446a45`, repository mounted read-only and network disabled | PASS — selected `114`, explicit third-party exclusions `2` |
| Bash 3.2 syntax | cached `bash@sha256:3a13e5da38baa575985778cd09ce8ac736d4b4dafc91a430e71271f6e5311b89` with network disabled | PASS — `bash -n scripts/ci/acceptance-isolated-home.sh` |
| Tracked source secret scan | `python3 scripts/ci/secret-scan.py` | PASS — `rule_version=1 scanned=345 skipped=237 findings=0` |

## Isolated doctor parity

Both commands ran against the same disposable HOME/XDG state and low-risk `research` profile, scoped to Cursor:

- text: `python3 scripts/agents/doctor.py --profile research --tool cursor`
- JSON: `python3 scripts/agents/doctor.py --profile research --tool cursor --json`

Result: PASS — text and JSON both reported `status=warn`, exit `0`, with identical counts `pass=12 warn=260 fail=0 skip=1 total=273`. A synthetic ephemeral credential marker was provided only in process environment to test redaction; it appeared in neither output and no log or secret was retained.

## Disposable HOME/XDG acceptance

Command: `BASH_BIN=bash bash scripts/ci/acceptance-isolated-home.sh`

Result: PASS. Final contract record:

```text
acceptance evidence: HOME=isolated cli=pass legacy_links=migrated writable_config=changed_then_unchanged agents_first=changed agents_second=unchanged metadata=inode+mtime+hash-stable backups=stable offline=stubbed secrets=none repo_status=unchanged repo_diff=unchanged repo_content=unchanged
```

The run migrated representative Nvim root and Logseq settings directory links without following them into repository sources, preserved runtime-only files, and verified the second config run did not rewrite targets/manifests or create backups. It then ran first-party Agent skills plus Cursor MCP/environment sync twice under the low-risk profile. Acquisition/network command stubs remained uncalled, no credential value was required, the first sync reported changes, and the second was fully unchanged. A full disposable-HOME snapshot compared path type/mode, inode, mtime, size, and SHA-256 before/after the second sync. Separate repository Git status, unstaged diff, staged diff, and full non-`.git` content snapshots had zero delta.

## Preserved caller state

- Staged `.gitignore` blob before and after implementation: `e367e954aa186cde4bd64dbd8e5dc96f1796f08d`.
- `.gitignore` worktree SHA-256: `4f06891022e4afaff46da637528439b89ae92842449700e076de9198a66f6b87`.
- `tasks.md` SHA-256 retained without checkbox edits: `199e6ebf4b58bf8fd17c11cd6d4169284b46b4daf76ed60e289dea575c66cb30`.
