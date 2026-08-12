---
name: dotf-install
description: "在已初始化的系统上按需安装/配置单个或多个模块，或全量补装。委托 dotf <module> -i/-c/-ic / dotf -a / dotf status / dotf retry。在用户要求装某个工具、配置某个模块、补装、全量装、跑 doctor 诊断、重试失败时使用。多用户/共用开发机默认走用户级模块，系统级模块（system/homebrew/docker/chsh）必须显式确认。新机首次初始化请改用 dotf-init。"
---

# dotf-install

在**已初始化**的系统上，按需额外安装/配置模块，或全量补装。薄包装：模块选择与多用户风险评估在本 skill 内做，实际执行一律委托 `bin/dotf`。

## 核心原则

1. **薄包装**：不重新实现安装逻辑，不改 `modules.yaml`。所有执行走 `dotf`。
2. **dry-run 优先**：装/配前先 `--dry-run` 让用户审计划。
3. **多用户安全第一**：读 `~/.dotf-env.md` 拿共用性判定；shared 下系统级模块必须显式确认，优先用户级替代。
4. **回写台账**：装完更新 `~/.dotf-env.md` 的「已初始化模块」与踩坑。

## 前置检查（每次进入先做）

1. **dotf 是否可用**：
   ```bash
   dotf __path          # 打印仓库根；失败说明未初始化或 PATH 缺失
   command -v dotf      # 或检查软链 ~/.config/dotfiles
   ```
   不可用 → 提示用户先走 `dotf-init` skill 完成 bootstrap，不要在这里硬装。
2. **读台账**：`~/.dotf-env.md` 若存在，拿共用性判定（solo/shared-user/shared-home）与已装模块；不存在 → 提示「建议先 dotf-init 记录环境」，或现场跑共用性探测（见 dotf-init 的探测命令）。

## 模块地图（按 group）

`modules.yaml` 是真相源；下表是 group 与多用户安全性的**速查**，非权威清单。权威查询：

```bash
python3 scripts/modules.py list                 # 全模块 + group + depends_on
python3 scripts/modules.py list --filter-os     # 当前 OS 适用
dotf <mod> -i --dry-run                         # 单模块计划预览
```

| group | 模块（示例） | 安装级别 | shared 下默认 |
|-------|--------------|----------|---------------|
| core | system, homebrew | **系统级**（sudo 装 / 改源） | ❌ 需显式确认 |
| core | sdk (mise), golang | 用户级（~/.local/share/mise, GOPATH） | ✅ 可直接装 |
| tools | delta, grepom, senv, mdserve, dws, ocr, npm | 多为用户级（cargo/go/bin） | ✅（确认依赖） |
| tools | ossutil, aws, aliyun, gcp | 用户级二进制 | ✅ |
| tools | vcpkg, d2 | 用户级 | ✅ |
| agents | agents, claude, cursor, kiro, opencode, codex, kimi-code, pi, zcode, minimax, qoder, trae-cli, codebuddy-code | 用户级 CLI + 配置 | ✅ |
| shell | git, zsh, starship | git 用户级配置；**zsh 可能 chsh**；starship 用户级 | ⚠️ zsh 见下 |
| editors | nvim, helix, zed | 用户级配置 + 可能装编辑器 | ✅（装编辑器时确认） |
| terminals | kitty, alacritty, wezterm, ghostty, iterm2 | 用户级配置；装终端可能系统级 | ✅（装终端时确认） |
| multiplexers | tmux, zellij | 用户级 | ✅ |
| desktop | hypr, fcitx5 | **系统级**（改桌面/输入法） | ❌ 需显式确认 |
| utils | fonts, yazi, k9s, shell_gpt, logseq | fonts 可能系统级；其余用户级 | ⚠️ fonts 确认 |

> 上述「级别」是基于现有脚本的归纳。无法确定时，**先 `--dry-run`** 看计划里有没有 sudo / 改 /etc / chsh。

### shared 下的用户级安全白名单

以下模块在 shared-user / shared-home 下通常可直接装（用户级、不改系统、不 chsh）：

```
sdk golang delta grepom senv mdserve dws ocr npm ossutil aws aliyun gcp vcpkg d2
agents claude cursor kiro opencode codex kimi-code pi zcode minimax qoder trae-cli
nvim helix tmux zellij yazi k9s shell_gpt
git starship（仅配置，不 chsh）
```

以下在 shared 下**必须显式确认**（系统级或影响他人）：

```
system homebrew hypr fcitx5 fonts（装到系统目录时） zsh（触发 chsh 时）
```

## Phases

用户意图决定 phase；识别不清时缺省 `list`。

### list（默认，只读）

1. 读台账 / 探测共用性。
2. 环境状态：`dotf status`（只读 L0）。
3. 可装模块：`python3 scripts/modules.py list --filter-os`（按 group 展示）。
4. 输出：当前已装/缺失、按 group 的可装模块、shared 下的安全标记。
5. 不改任何状态。

### install `<mod...>`

装一个或多个模块（可连带配置）。

```bash
dotf <mod> -i               # 仅安装
dotf <mod> -ic              # 安装 + 配置
dotf <mod1> <mod2> -ic      # 多模块
dotf <mod> -i --dry-run     # 先看计划
dotf <mod> -i --yes         # 非交互（shared 下系统级动作仍会确认）
```

流程：
1. 先 dry-run 看计划，识别系统级动作（sudo/chsh/改 /etc/docker 组）。
2. shared 下遇系统级动作 → 展示影响范围，要求显式同意；不同意则跳过该模块或换用户级替代。
3. shared 下遇 zsh chsh → 默认拒绝 chsh，给用户级绕过（见下）。
4. 执行（用户确认后；非 TTY 需 `--yes`）。
5. 成功后回写台账「已初始化模块」；失败记踩坑。

### config `<mod...>`

仅配置（不装），例如刷新 nvim/tmux 配置软链。

```bash
dotf <mod> -c
dotf <mod> -c --yes
dotf agents -c              # 聚合同步 skills + MCP
dotf agents -c --tool cursor  # 过滤同步目标
```

配置类基本是用户级文件软链，shared 下也安全。但 `dotf agents -c` 会写各工具的 skills/commands 目录——确认目标路径在用户 HOME 下（如 `~/.zcode`、`~/.claude`），不污染全局。

### all（全量补装）

```bash
dotf -a                     # 装全部 + 配全部（不含 doctor），按当前 OS 过滤
dotf -a --dry-run           # 先看计划
dotf -a --profile remote    # 指定使用场景 profile
```

shared 下 **all 会包含 system 等系统级模块** → 必须先 dry-run，逐项确认或改用更小的 profile + 手动补用户级模块。

### doctor `[mod...]`

诊断（只读，L0 默认 / `--deep` 跑 L1）。

```bash
dotf <mod> -d               # 单模块
dotf -d -a                  # 全量
dotf agents -d --deep --json  # agents 深度诊断（脱敏 JSON）
```

### retry

重试最近报告中失败的动作（读 `dotf` 的执行报告，自动重建失败子计划）。

```bash
dotf retry
```

## chsh 绕过（shared 下装 zsh 时）

`zsh` 配置（`.zshrc` 等）是用户级软链，不 chsh 也能用。shared 下推荐不改默认 shell：

```bash
# 方案 A：~/.bashrc 末尾自动切（仅当前用户，不影响他人登录默认 shell）
[ -n "$PS1" ] && [ -x "$(command -v zsh)" ] && exec zsh -l

# 方案 B：仅本会话
exec zsh -l

# 方案 C：终端模拟器指定启动命令为 zsh
```

在 `dotf` 的 chsh 副作用确认处选择「否」，配置文件仍会就位。

## 依赖处理

`modules.yaml` 的 `depends_on` 由 planner 自动拓扑排序，**不需要手动装依赖**。例如：

- `golang` depends_on `sdk` → `dotf golang -i` 会自动带上 sdk
- `senv`/`grepom`/`mdserve` depends_on `golang` → 链式带上 sdk
- `delta` depends_on `git`

dry-run 计划里会展示完整依赖链，确认后再执行。

## 常见交互

| 用户说 | 行为 |
|--------|------|
| 「装一下 nvim」「配置 tmux」 | install/config 单模块；先 dry-run |
| 「补装所有」 | all；shared 下先 dry-run 逐项确认 |
| 「看看还缺啥」 | list（dotf status + 模块清单） |
| 「诊断一下 xx」 | doctor |
| 「重试失败的」 | retry |
| 「装 nvim 和 tmux」 | `dotf nvim tmux -ic` |
| 「这是公司机，装 xx」 | 按台账 shared 处理；系统级模块确认；用户级直接装 |
| 「新机器初始化」 | **改用 dotf-init skill** |

## 安全与边界

- **绝不**在 shared 下未经确认装系统级模块（system/homebrew/hypr/fcitx5/系统字体/触发 chsh 的 zsh）。
- **绝不**自己拼 sudo 命令——所有 sudo 走 `dotf` 已有的确认流程。
- 配置写入前确认目标在用户 HOME 下；shared-home 下尤其小心同名文件，依赖 `dotf` 的备份机制。
- `dotf agents -c` 等聚合同步，确认目标路径不污染全局/他人目录。
- 装完回写台账；失败记踩坑（现象 → 原因 → 解决/绕过）。
- 脚本若行为与 skill 描述不符（如某「用户级」模块实际 sudo 了）：记录踩坑，提示用户「可能需更新 dotf 脚本或本 skill 的模块地图」——保持脚本与 skill 的兼容性反馈闭环。
- 台账 `~/.dotf-env.md` 禁止写入密钥/token/密码明文。
