---
id: repo-manager
name: repo-manager
description: 通过 `grepom`（首选，跨平台批量操作工作区多仓）和 `glab`（GitLab 专用回退：issues、variables、snippets、细粒度 MR 参数）管理多个 GitLab / GitHub / 通用 Git 仓库。若已有 `.repo-manager.md` 则维护 cwd 台账（创建前先询问）。在用户要求跨多仓 clone、sync、list、status、pull、search、scan、push、创建 MR/PR、看 CI pipeline、处理 `.grepom.yml`、从远端 group/org 发现新仓、push 前扫密钥、打 release tag、或在工作区仓库间跳转时使用。不要用于单文件 git 操作、特定 diff 的 code review、或与仓库基础设施无关的工作。
---

# 仓库管理

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

两层 CLI：跨仓批量优先用 `grepom`；`grepom` 覆盖不到时再用 `glab`。

配置查找：`grepom` 从当前目录或任意父目录读取 `.grepom.yml`。用 `-c <path>` 覆盖。

## 台账（`.repo-manager.md`）

在**当前工作目录**维护 `.repo-manager.md`，记录本工作区的仓库台账与操作手帐，供人与后续 agent 复用。

### 创建门禁（强制）

| 情况 | 行为 |
|------|------|
| `./.repo-manager.md` **不存在** | **禁止自动创建**。向用户提示：「当前目录没有 `.repo-manager.md`，是否创建台账？」仅当用户明确同意（如「创建」「写台账」「初始化 .repo-manager.md」）后再按下方模板新建。 |
| `./.repo-manager.md` **已存在** | **自动更新**：会话开始先读；有实质操作或新踩坑后立刻写回，无需再问。 |
| 用户明确要求创建/初始化台账 | 即使原先不存在，也按模板创建并写入本次信息。 |

路径始终是 **cwd 下的** `./.repo-manager.md`（不要写到 home、cache 或父目录，除非用户另行指定）。

### 何时读写

1. **任何 repo-manager 操作开始时**：若文件存在，先读一遍——优先采用其中的 resource/group 约定、exclude、鉴权环境变量名、已知坑。
2. **文件存在且完成实质操作后**：自动追加/更新手帐与稳定信息（见下）。只读查询（如单纯 `status` / `list` 且无发现）可不写。
3. **遇到坑时立刻写入**：鉴权失败、sync/clone 异常、prune 误伤、secret scan 命中策略、host/protocol 踩坑等——确认原因或绕过后马上记入「踩坑」，同一问题更新已有条目，不重复堆砌。
4. **文件不存在时**：照常执行 grepom/glab；仅提示一次可建台账，**不**因提示未答复而阻断操作。

### 应记录的内容

- **概览**：工作区用途、`.grepom.yml` 位置（相对 cwd）、主要 resource / group / vgroup、本地 base 路径约定。
- **约定**：常用 filter（`--group` / `--resource` / `--vgroup`）、exclude 策略、token 环境变量**名**（不写值）、SSH/HTTP 协议偏好。
- **手帐**：有状态变化的操作——`sync` / `clone` / `pull` / `prune` / `push` / `mr` / `tag` / 批量 discovery 等；一行一条，含日期与结果摘要。
- **踩坑**：本工作区特有问题与绕过方式。

### 文件模板

新建时使用（按实际删减，保持简洁）：

```markdown
# 仓库管理 — <工作区目录名>

## 概览

- 一句话说明本工作区管理哪些仓库
- 配置：`.grepom.yml`（或相对路径）
- base / 主要 group、resource

## 约定

- 常用命令或 filter
- 鉴权：环境变量名（如 `${GITLAB_TOKEN}`），禁止写明文
- exclude / prune 注意点

## 手帐

- YYYY-MM-DD：操作 → 范围 → 结果（如 sync 新增 N 仓；clone 失败的 repo）

## 踩坑

- YYYY-MM-DD：现象 → 原因 → 解决/绕过
```

### 写入原则

- 只写与**多仓管理 / 同步 / 鉴权 / 扫描 / MR·流水线**相关的信息；不写业务代码细节。
- **禁止**写入 token、密码、私钥、内部未公开 URL 中的凭据部分。
- 手帐要可回溯：后人能看出「何时对哪些 group 做了什么」。
- 稳定约定放「概览/约定」，一次性操作放「手帐」；不要把整份 `grepom status` 原文贴进文件。
- 用户若明确要求不提交该文件，提醒可加入 `.gitignore`，但仍在本地维护。

## 工具选择

| 需求 | 工具 |
|------|------|
| 跨多仓批量 clone / pull / status | `grepom` |
| 从远端 group/org 发现新仓 | `grepom sync` + `grepom clone` |
| 跨平台（GitLab + GitHub + 通用 Git） | `grepom` |
| 带 secret scan 的安全 push | `grepom push` |
| 仅 GitLab：issues、variables、snippets、raw API | `glab` |
| 细粒度 MR 参数（`--squash-before-merge`、`--label`、`--reviewer`、`--remove-source-branch`） | `glab mr create` |

`glab` 可选。安装：`brew install glab` / `apt install glab` / `scoop install glab`。多数 MR/PR 用 `grepom mr` 即可。

## 初始化（每个工作区一次）

```bash
# 交互式 — 写入 ./.grepom.yml
grepom init

# 非交互
grepom init --base ~/projects --provider gitlab \
  --url https://gitlab.example.com --token '${GITLAB_TOKEN}'

# 之后追加 resource / group / 独立仓库
grepom add resource --name work-gl --provider gitlab \
  --url https://gitlab.example.com --token '${GITLAB_TOKEN}'

grepom add group --name frontend --resource work-gl \
  --path my-org/frontend --recursive

grepom add repo --name dotfiles --resource github \
  --url https://github.com/me/dotfiles.git

# 重新生成一份干净的 example 配置
grepom example
```

token 值用 `${ENV_VAR}` 替换。密钥放在 shell 环境（1Password CLI / direnv / vault），禁止写进 YAML 明文。

## 发现与克隆

```bash
grepom sync                     # 从远端 group 填充配置（不 clone）
grepom clone                    # 全量克隆，4 worker 并行
grepom clone --group frontend   # 单个 group
grepom clone --resource work-gl # 某个 resource 下全部仓
grepom clone --concurrency 1    # 串行（compat）
grepom clone web-app            # 按名称克隆单仓
grepom clone --vgroup work      # 虚拟 group
```

`sync` 只追加新仓，从不删除。在 YAML 里改完 `exclude_repos` 后，用 `grepom prune --apply` 从磁盘去掉已排除的克隆。

## 工作区卫生

```bash
grepom status                   # 各仓 dirty / ahead 摘要
grepom list                     # 仅需关注的仓（默认 filter）
grepom list --all               # 全部仓，含干净的
grepom list --no-push           # 仅未 push
grepom list --no-commit         # 仅 dirty
grepom list groups              # 列出已配置 group
grepom list --remote            # 查 provider API，不用本地配置
grepom search web --group fe    # 大小写不敏感子串搜索
grepom pull                     # 更新干净且在默认分支的仓（并行）
grepom pull --force             # 不论状态都更新
grepom dedup                    # 查 group 内/跨 group 重复
grepom prune                    # dry-run：磁盘上仍在的已排除仓
grepom prune --apply            # 真正删除
```

## 安全 push 与 secret scan

```bash
grepom push                     # gitleaks scan → git push；命中则中止
grepom push -f                  # force（会警告）
grepom push -- origin main      # 透传给 git push
grepom scan                     # 扫工作区文件（gitleaks 规则）
grepom scan --history           # 含 git 历史（含已删 commit）
grepom scan --format json -o report.json
grepom scan -p /path/to/repo    # 临时路径，不需要配置
grepom scan --gitleaks-config rules.toml   # 项目级 allowlist
```

`grepom push` **不需要**配置文件，任意 git 仓库都能用。默认：先 scan，干净才 push。

## MR / PR / Pipeline

```bash
# MR/PR — 从 HEAD 自动推断 branch、target、title
grepom mr
grepom mr --from feat-x --to main --title "Add X" --draft
grepom mr --body-file desc.md --web    # 用浏览器打开，不用 CLI
grepom pr                              # `mr` 的别名

# Pipeline
grepom pipeline list                   # 最近的 pipeline
grepom pipeline watch                  # 等待当前 pipeline
grepom watch                           # 从 cwd 自动识别仓
grepom watch web-app --id 1234         # 指定仓 + pipeline
```

`grepom mr` 从 HEAD commit 读 title 和 body。先写好 Conventional Commit 主题。

需要 `--squash-before-merge`、`--label`、`--assignee`、`--reviewer`、`--remove-source-branch`、`--milestone` 时，回退到 `glab mr create`。

## Release tag

```bash
grepom tag                       # v0.1.5 → v0.1.6（lightweight）
grepom tag -m "release notes"    # annotated
grepom tag -p                    # push 到全部 remote
grepom tag -t -p                 # t-prefix（测试 release）
grepom tag -w                    # tag 后 watch pipeline
grepom tag --dry-run             # 只预览
```

## 跳转

在 `~/.zshrc`（或 `~/.bashrc`）加一次：

```bash
eval "$(grepom dir --shell)"
```

然后：

```bash
gcd web-app                      # 精确匹配 → cd
gcd web                          # 子串；唯一则 cd，多个则列出
grepom dir web-app               # 可脚本化：cd "$(grepom dir web-app)"
```

## glab：GitLab 专用回退

单仓范围。`grepom` 覆盖不到时再用。

```bash
glab auth login --hostname gitlab.example.com
glab repo clone gitlab.example.com/group/repo
glab mr create --title "..." --description "..." --target-branch main \
  --squash-before-merge --remove-source-branch --label ~"feature" --reviewer alice
glab mr list
glab issue list --assignee @me
glab ci status
glab ci trace                    # 实时 job 日志
glab variable list               # CI/CD variables
glab api projects/:id/variables  # raw API
```

## 多实例鉴权

`glab` 按 hostname 存凭据，没有 `switch` 命令。每个实例登录一次，再按命令或当前 shell 选 host：

```bash
# --stdin 避免 token 进 shell history
glab auth login --hostname gitlab.example.com --stdin
glab auth login --hostname gitlab.other.com --stdin
glab auth status --all

GITLAB_HOST=gitlab.other.com glab mr list   # 单条命令
export GITLAB_HOST=gitlab.example.com       # 当前 shell
glab auth logout --hostname gitlab.other.com
```

host 解析顺序：`GITLAB_HOST` → 当前仓库 Git remote → `~/.config/glab-cli/config.yml`。无图形界面登录用 `--device`（GitLab 17.9+）。凭据默认走 OS keyring；仅必要时才用 `--insecure-storage`。

对 `grepom`：每个 GitLab 实例建模成命名 `resource`，再把 group 绑上去：

```yaml
resources:
  corp:
    provider: gitlab
    url: https://gitlab.example.com
    token: ${CORP_GITLAB_TOKEN}
  oss:
    provider: gitlab
    url: https://gitlab.com
    token: ${OSS_GITLAB_TOKEN}

groups:
  - name: backend
    resource: corp
    path: my-org/backend
    recursive: true
```

按需用 `grepom clone --resource corp`、`grepom status --resource corp` 或 `grepom pull --resource corp`；每个 resource 可覆盖自己的 `token`/`ssh_key`。token 放环境变量，用最小权限 PAT；泄露则立刻 revoke/rotate。

## 维护

```bash
grepom update                    # 自更新到最新 release
grepom completion zsh > ~/.zsh/completions/_grepom   # shell 补全
grepom version                   # 已安装版本
```

## 约定

- **token 来源**：YAML 里一律 `${ENV_VAR}` 占位；密钥经 1Password CLI / direnv / vault 导出，禁止明文。
- **先 commit 再 MR**：`grepom mr` 读 HEAD 消息，先写好 Conventional Commit 主题。
- **未经用户确认，禁止 `--force` push**。
- **过期配置**：`sync` 只追加；上游仓改名/删除时手动改配置，或用 `grepom init` + `grepom add group` 重建。
- **verbose**：命令异常时加 `-v` 看调试输出。
- **台账**：遵守 `.repo-manager.md` 创建门禁——禁止自动创建；仅文件已存在时自动更新（见「台账」节）。

## 不确定时

```bash
grepom --help
grepom <command> --help
glab --help
```

优先跑真实 `--help`，不要猜参数——两个工具迭代快，flag 会变。

## 踩坑（可复用经验）

可复用的踩坑经验。**只记跨实例通用的规律**，具体 host / IP / token / 路径等特例不放这里。

### glab CLI

- **HTTP-only 实例必须显式 `--api-protocol http`**：默认走 https，遇到 TLS 错误优先怀疑这个 flag 没带。
  ```bash
  glab auth login --hostname <host> --api-protocol http --git-protocol ssh --stdin
  ```
- **glab 全局默认 host 是 `gitlab.com`**：所有 `glab api /xxx`、`glab mr list` 等命令不显式 `--hostname` 都会用到默认值。多实例环境永远带 `--hostname <host>` 或 `GITLAB_HOST=<host>`。
- **keyring 不可用时 fallback 到 plaintext**（常见于 Linux server / 无 desktop env）：token 落到 `~/.config/glab-cli/config.yml`（权限 0600）。可手动 `chmod 600` 加固；启用 desktop 后再 `glab auth login` 一次会搬回 keyring。
- **`glab mr list` 在 cwd repo 没匹配 host 时报 "remote not known"**：用 `--hostname <host> -R <group>/<repo>` 解决，或 `cd` 到目标 repo。

### GitLab REST API

- **GitLab 17.9+ transfer API 用 `PUT /projects/:id/transfer`**（不是 `POST`）。参数是 `namespace=<group_path>`，不是 `namespace_id=<id>`。
  ```bash
  glab api --hostname <host> -X PUT projects/<id>/transfer -f namespace=<group_path>
  ```
- **`DELETE /projects/:id` 默认是软删除**：标 `marked_for_deletion_at` + 30 天后悔期。path 自动加 `-deletion_scheduled-<id>` 后缀防冲突。
- **恢复软删除**：`POST /projects/:id/restore`，path 自动回到原值。
- **物理硬删要走 admin 内部接口**：`glab` 不暴露；要在 GitLab 主机上 `gitlab-rails console` 跑 `Project.unscoped.find(<id>).really_destroy!`。
- **搜 namespace 不要只查一处**：自托管 group/user 命名易混，三个 API 并行查：
  ```bash
  glab api --hostname <host> 'groups?search=<kw>'
  glab api --hostname <host> 'users?username=<kw>'
  glab api --hostname <host> 'namespaces?search=<kw>'   # 同时含 group + user
  ```
- **`/api/v4/version` 401 不一定是 TLS 错**：很多自托管实例把 version 也要求认证，反而说明 HTTP/API 路径对，继续带 token 测 `/user` 即可。

### grepom 配置与 GitLab 分组

- **配置作用域要先确认**：grepom 会从当前目录向上查找 `.grepom.yml`。在项目内新增本地配置后，它会遮蔽父目录配置；需要操作另一份配置时显式使用 `grepom -c /path/to/.grepom.yml ...`，避免把仓库克隆到错误的 workspace。
- **最小 GitLab 配置**：`base` 是相对于配置文件目录的克隆根目录；分组的 `local_path` 再相对于该 `base` 计算。例如 `base: ./repos`、`local_path: ./team`、远程路径 `team/service` 最终落在 `repos/team/service`。
  ```yaml
  base: ./repos
  resources:
    gitlab-primary:
      provider: gitlab
      url: https://gitlab.example.com
      token: ${GITLAB_TOKEN}
  groups:
    - name: team
      resource: gitlab-primary
      path: team
      local_path: ./team
      recursive: true
  repos: []
  ```
- **推荐初始化顺序**：先用 `grepom init --base ./repos --provider gitlab --url <host> --token '${TOKEN_ENV}'` 生成配置，再把 resource 名称调整为有意义的实例名（例如 `gh`），最后用 `grepom add group --name <name> --resource <resource> --path <group-path> --local-path ./<local-dir> --recursive` 登记分组。不要把 token 明文写入 YAML。
- **追踪与克隆分两步**：`grepom sync --group <group>` 只向配置追加远程发现的新仓库，不会自动克隆；确认发现结果后运行 `grepom clone --group <group>`。全量场景可使用 `grepom clone --resource <resource>`，单仓库使用 `grepom clone <repo-name>`。
- **同步结果要核对**：sync 后用 `grepom list groups` 检查 group/resource/path/repo 数量，再用 `grepom list --all` 确认仓库状态；clone 后进入目标仓库执行 `git status --short --branch`，或运行 `grepom status`。
- **HTTP-only 或 TLS 异常的自托管 GitLab**：资源 URL 显式写 `http://<host>`，避免 grepom 先尝试 HTTPS 再回退并产生额外延迟。若 `grepom add group` 将 URL 规范化为无 scheme 的 host，可手动恢复 `http://` 后再次用 `grepom list` 校验配置仍可解析。API 查询和 glab 操作同时显式带 `--hostname <host>`。
- **SSH URL 形态要注意**：对带 GitLab resource 的 standalone repo，优先把 `url` 写成远程相对路径（如 `group/repo.git`），让 grepom 组合成 `git@<host>:group/repo.git`；直接填 `ssh://git@<host>/group/repo.git` 可能被重复拼接成错误地址。分组 sync 通常会自动写入可用的 HTTP clone URL，SSH clone 仍会优先尝试本机密钥。
- **新建远程项目后的登记方式**：远程项目已存在于已追踪的 GitLab group 时，重新执行 `grepom sync --group <group>` 即可发现；不在已追踪 group 中时使用 `grepom add repo --name ... --resource ... --url ...`。创建远程项目属于 GitLab API 能力，grepom 未覆盖时用 `glab repo create <host>/<group>/<repo> --skipGitInit`，创建后再回到 sync/clone 流程。
- **克隆基目录应纳入忽略**：如果 `base` 指向项目内的 `repos/`，将 `repos/` 加入项目 `.gitignore`，避免把被管理仓库的工作树误提交到当前配置仓库；配置文件 `.grepom.yml` 是否提交则按项目约定处理。
- **安全推送**：完成仓库内提交后优先用 `grepom push -- origin <branch>`，它会先执行 secret scan；扫描包含大二进制文件时可能较安静且耗时，等待命令返回，不要在未确认结果前重复 push。发现命中时先清理或配置 allowlist，不要默认使用 `-f`。
