---
id: repo-manager
name: repo-manager
description: Manage multiple GitLab / GitHub / generic Git repositories via `grepom` (primary, cross-platform batch operations on a workspace of repos) and `glab` (GitLab-specific fallback for issues, variables, snippets, and fine-grained MR flags). Use when the user asks to clone, sync, list, status, pull, search, scan, push, create MR/PR, or watch CI pipelines across many repos; when working with `.grepom.yml` configs; when discovering new repos in a remote group/org; when scanning for secrets before push; when bumping release tags; or when quickly jumping between repo directories in a workspace. Do NOT use for single-file git operations, code review of specific diffs, or work that has nothing to do with repository plumbing.
---

# repo-manager

Two CLI layers. Prefer `grepom` for cross-repo batch work; reach for `glab` only when grepom doesn't cover the operation.

Config lookup: `grepom` reads `.grepom.yml` from the current directory or any parent. Override with `-c <path>`.

## Tool selection

| Need | Tool |
|------|------|
| Batch clone / pull / status across many repos | `grepom` |
| Discover new repos from a remote group/org | `grepom sync` + `grepom clone` |
| Cross-platform (GitLab + GitHub + generic) | `grepom` |
| Safe push with secret scan | `grepom push` |
| GitLab-only ops: issues, variables, snippets, raw API | `glab` |
| Fine-grained MR flags (`--squash-before-merge`, `--label`, `--reviewer`, `--remove-source-branch`) | `glab mr create` |

`glab` is optional. Install via `brew install glab` / `apt install glab` / `scoop install glab`. For most MR/PR work, `grepom mr` is enough.

## Setup (one-time per workspace)

```bash
# Interactive — writes ./.grepom.yml
grepom init

# Non-interactive
grepom init --base ~/projects --provider gitlab \
  --url https://gitlab.example.com --token '${GITLAB_TOKEN}'

# Append resources / groups / standalone repos later
grepom add resource --name work-gl --provider gitlab \
  --url https://gitlab.example.com --token '${GITLAB_TOKEN}'

grepom add group --name frontend --resource work-gl \
  --path my-org/frontend --recursive

grepom add repo --name dotfiles --resource github \
  --url https://github.com/me/dotfiles.git

# Regenerate a clean example config
grepom example
```

Token values use `${ENV_VAR}` substitution. Keep secrets in the shell env (1Password CLI / direnv / vault); never literal in YAML.

## Discover and clone

```bash
grepom sync                     # populate config from remote groups (no clone)
grepom clone                    # clone everything, 4 workers in parallel
grepom clone --group frontend   # single group
grepom clone --resource work-gl # all repos from one resource
grepom clone --concurrency 1    # sequential (compat mode)
grepom clone web-app            # single repo by name
grepom clone --vgroup work      # virtual group of groups
```

`sync` only adds new repos — it never removes. After editing `exclude_repos` in YAML, run `grepom prune --apply` to drop the now-excluded clones from disk.

## Workspace hygiene

```bash
grepom status                   # dirty / ahead summary per repo
grepom list                     # only repos needing attention (default filter)
grepom list --all               # every repo, including clean
grepom list --no-push           # only unpushed
grepom list --no-commit         # only dirty
grepom list groups              # list configured groups
grepom list --remote            # query provider API instead of local config
grepom search web --group fe    # case-insensitive substring search
grepom pull                     # update clean, default-branch repos (parallel)
grepom pull --force             # update regardless of state
grepom dedup                    # find duplicates within/across groups
grepom prune                    # dry-run: list excluded repos still on disk
grepom prune --apply            # actually delete
```

## Safe push and secret scan

```bash
grepom push                     # gitleaks scan → git push; aborts on hit
grepom push -f                  # force (with warning)
grepom push -- origin main      # pass through to git push
grepom scan                     # scan workspace files (gitleaks rules)
grepom scan --history           # also scan git history (incl. deleted commits)
grepom scan --format json -o report.json
grepom scan -p /path/to/repo    # ad-hoc path, no config needed
grepom scan --gitleaks-config rules.toml   # project-specific allowlist
```

`grepom push` does NOT require a config file — it works in any git repo. Default behavior: scan, then push only if clean.

## MR / PR / Pipeline

```bash
# MR/PR — auto-detects branch, target, title from HEAD
grepom mr
grepom mr --from feat-x --to main --title "Add X" --draft
grepom mr --body-file desc.md --web    # open browser instead of CLI
grepom pr                              # alias of `mr`

# Pipeline
grepom pipeline list                   # recent pipelines
grepom pipeline watch                  # wait for current
grepom watch                           # auto-detect repo from cwd
grepom watch web-app --id 1234         # specific repo + pipeline
```

`grepom mr` reads the title and body from the HEAD commit. Write a Conventional Commit subject first.

When you need `--squash-before-merge`, `--label`, `--assignee`, `--reviewer`, `--remove-source-branch`, `--milestone` — fall back to `glab mr create`.

## Release tags

```bash
grepom tag                       # v0.1.5 → v0.1.6 (lightweight)
grepom tag -m "release notes"    # annotated
grepom tag -p                    # push to all remotes
grepom tag -t -p                 # t-prefix (test release)
grepom tag -w                    # tag, then watch pipeline
grepom tag --dry-run             # preview only
```

## Navigation

Add once to `~/.zshrc` (or `~/.bashrc`):

```bash
eval "$(grepom dir --shell)"
```

Then:

```bash
gcd web-app                      # exact match → cd
gcd web                          # substring; one match → cd, many → list
grepom dir web-app               # scriptable: cd "$(grepom dir web-app)"
```

## glab: GitLab-specific fallbacks

Single-repo scope. Use when grepom doesn't cover it.

```bash
glab auth login --hostname gitlab.example.com
glab repo clone gitlab.example.com/group/repo
glab mr create --title "..." --description "..." --target-branch main \
  --squash-before-merge --remove-source-branch --label ~"feature" --reviewer alice
glab mr list
glab issue list --assignee @me
glab ci status
glab ci trace                    # live job logs
glab variable list               # CI/CD variables
glab api projects/:id/variables  # raw API
```

## Maintenance

```bash
grepom update                    # self-update to latest release
grepom completion zsh > ~/.zsh/completions/_grepom   # shell completion
grepom version                   # installed version
```

## Conventions

- **Token sources**: always `${ENV_VAR}` placeholders in YAML; export secrets via 1Password CLI / direnv / vault — never literal.
- **Commit before MR**: `grepom mr` reads the HEAD message — write a Conventional Commit subject first.
- **Never `--force` push without confirming with the user**.
- **Stale config**: `sync` only adds; if upstream repos are renamed/removed, edit the config manually or rebuild with `grepom init` + `grepom add group`.
- **Verbose mode**: add `-v` for debug output when a command misbehaves.

## When unsure

```bash
grepom --help
grepom <command> --help
glab --help
```

Prefer running actual help over guessing — both tools iterate quickly and flags change.
