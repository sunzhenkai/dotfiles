---
name: dotf-init
description: "新系统/新用户首次初始化：探测运行时与多用户共用性，选定 profile，委托 bootstrap.sh + dotf init 完成从裸机到可用环境。在用户要求初始化新机、setup、bootstrap、dotf init、装机、配置新开发环境时使用。多用户/共用开发机默认走用户级安装，系统级操作（sudo/chsh/改 /etc）必须显式确认。在已初始化的系统上补装单个模块请改用 dotf-install。"
---

# dotf-init

把一台「裸机」（或一个新用户账号）带到一个**可用 profile** 状态。薄包装：环境判断与多用户风险评估在本 skill 内做，实际安装/配置一律委托 `scripts/bootstrap.sh` 与 `bin/dotf init`。

## 核心原则

1. **薄包装**：不重新实现安装逻辑，不改 `modules.yaml` / `dotf`。所有执行都走 `bootstrap.sh` 与 `dotf`。
2. **dry-run 优先**：任何会改系统状态的操作，先 `--dry-run` 让用户审计划。
3. **多用户安全第一**：公司开发机可能是多用户 / 共用账号。**不擅自 sudo、不改 /etc、不 chsh**——shared 场景下这些操作必须显式确认，并优先建议用户级替代。
4. **写台账**：维护 `~/.dotf-env.md` 记录这台机器的 profile 与共用性判定，供下次复用。

## 前置定位

本 skill 只负责「首次初始化」。若用户只是想补装某个模块（如「装一下 nvim」「配置 tmux」），应改用 `dotf-install` skill，不要走 init 全流程。

判断依据：
- 用户说「初始化新机」「setup 这台机器」「bootstrap」「dotf init」「装机」→ 本 skill
- 用户说「装个 xx」「配置 xx」「补一下 xx」→ `dotf-install`

## 两个真相源

| 文件 | 作用 | 在哪 |
|------|------|------|
| `modules.yaml` | 模块能力与路径（install/config/doctor/os/depends_on/group） | 仓库根 |
| `profiles.yaml` | 使用场景 profile（minimal/remote/desktop/full） | 仓库根 |

OS 检测、模块清单、profile 展开都由 `dotf` 自己读这两个文件完成，**skill 不要重复维护模块清单**。需要列模块时调用：

```bash
dotf init --list                    # OS profile + 使用场景 profile
python3 scripts/modules.py list     # 全模块（含 group/depends_on）
```

## 多用户共用性判定（核心，所有 phase 前必做）

调用任何写操作前，先判定这台机器的共用性，写入 `~/.dotf-env.md`，并据此决定 profile 推荐与门禁。

### 探测命令（只读）

```bash
# 1. 这台机器有多少个真实人类账号？
getent passwd | awk -F: '$3 >= 1000 && $3 < 65534 {print $1}'   # Linux
dscl . list /Users UniqueID | awk '$2 >= 500 {print $1}'        # macOS

# 2. 当前账号是不是「共用账号」典型名？
echo "$USER"   # dev/shared/deploy/build/team/guest → 疑似共用

# 3. 现在还有谁登录着？
who            # 或 w

# 4. HOME 是不是共用/非标？
echo "$HOME"   # /home/dev /shared /workspace → 疑似共用 HOME

# 5. 是不是容器/一次性环境？
[ -f /.dockerenv ] && echo "container"
```

### 判定结论（三档）

| 结论 | 触发条件 | 默认策略 |
|------|----------|----------|
| `solo` | 只有当前一个真实用户，HOME 私有 | 可 `full`/`remote`，允许系统级操作（仍需 dotf 的副作用确认） |
| `shared-user` | 存在多个真实用户账号，但当前 HOME 私有 | 默认 `minimal` + 用户级模块；系统级操作（system/docker/改 /etc）需显式确认 |
| `shared-home` | HOME 共用或 `$USER` 是共用账号名 | 默认 `minimal`，**禁止** chsh；系统级操作一律先问 |

判定模糊时按更保守的那档处理（solo vs shared-user 不清 → 当 shared-user），并向用户说明假设。

### profile 推荐矩阵

| 场景 | 共用性 | 推荐 profile | 说明 |
|------|--------|--------------|------|
| 个人桌面 | solo | `full` | 当前 OS 适用全集 |
| 个人远程/服务器 | solo | `remote` | minimal + nvim/tmux/cli 工具/agents |
| 公司开发机（独占账号） | shared-user | `minimal` 起步，按需加用户级模块 | 不装 system 系统包，不 chsh |
| 公司共用账号/共用 HOME | shared-home | `minimal` | 仅用户级，绝不 chsh |
| 仅想试一下 | 任意 | 先 `--dry-run` 看计划 | |

profile 模块组成见 `profiles.yaml`：`minimal` = system/sdk/git/zsh/starship；`remote` = minimal + golang/nvim/tmux/delta/grepom/agents；`full` = 当前 OS 全集。

**注意**：即便 `minimal` 也含 `system`（会 sudo 装系统包）和 `zsh`（可能 chsh）。在 shared 场景下，要明确告知用户这两点，并准备好用户级绕过方案（见下「chsh 绕过」）。

## 系统级风险点清单（shared 下要逐项把关）

| 模块 | 风险动作 | shared 下处理 |
|------|----------|---------------|
| `system` | `sudo apt/dnf/pacman install` 大批系统包、改软件源 | 默认跳过或要求显式确认；告知「这会改动全局，影响所有用户」 |
| `system`(docker) | `sudo usermod -aG docker`、`systemctl enable --now docker` | 显式确认；docker 组等价 root，shared 下尤其敏感 |
| `zsh` | `chsh -s` 改默认 shell（`system.sh:386`） | shared 下**默认拒绝** chsh，给绕过方案 |
| `homebrew` | 装到 `/opt/homebrew` 或 `/home/linuxbrew`，多用户权限易乱 | shared 下确认安装路径与组权限策略 |
| `fonts` | 装到系统字体目录 | 用用户级字体目录 `~/.local/share/fonts`（Linux）/ `~/Library/Fonts`（macOS） |

### chsh 绕过（不改默认 shell 也能用 zsh）

shared-home / shared-user 下，推荐以下任一替代 `chsh`：

```bash
# 方案 A：在 ~/.bashrc 末尾自动切（仅当前用户生效，不影响他人登录默认 shell）
# 仅当交互式 shell 且 zsh 存在时
[ -n "$PS1" ] && [ -x "$(command -v zsh)" ] && exec zsh -l

# 方案 B：仅本会话
exec zsh -l

# 方案 C：终端模拟器里指定启动命令为 zsh（不影响 SSH 登录 shell）
```

`dotf` 的 zsh 配置（`.zshrc` 等）是软链到 HOME 的用户级文件，不 chsh 也能用——只是登录默认 shell 还是原来的。要把这一点讲清楚。

## 环境台账 `~/.dotf-env.md`

记录这台机器的初始化状态，供下次（人或 agent）复用。**路径固定在用户 HOME**，不进任何仓库。

### 创建门禁

| 情况 | 行为 |
|------|------|
| `~/.dotf-env.md` **不存在** | 完成探测后提示：「是否把这台机器记录到 `~/.dotf-env.md`？」用户同意后按模板创建。`--dry-run` / `check` 阶段不创建。 |
| **已存在** | 任何 phase 开始先读；完成实质操作后自动更新，无需再问。 |

### 模板

```markdown
# dotf-env — <hostname>

## 机器

- hostname: ...
- OS: ubuntu 22.04 / darwin 14 / ...
- 检测时间: YYYY-MM-DD

## 共用性

- 判定: solo | shared-user | shared-home
- 依据: <账号数 / HOME 路径 / 登录者 / 是否容器>

## 初始化

- profile: minimal | remote | desktop | full
- 已初始化模块: system, sdk, zsh, ...
- chsh: yes | no | skipped(shared)
- 最后初始化: YYYY-MM-DD

## 踩坑

- YYYY-MM-DD：现象 → 原因 → 解决/绕过
```

### 写入原则

- 只写环境事实与决策（profile、共用性、chsh 取舍、踩坑）；**不写**密钥、token、密码。
- 踩坑要可操作：下次 agent 按条目能避开或复现修复。
- 不要把临时命令输出、pid 写进台账。

## Phases

用户意图决定 phase；识别不清时缺省 `check`。

### check（默认，只读）

目标：让用户（和 agent）看清这台机器现状，不改任何状态。

1. 读 `~/.dotf-env.md`（若有）。
2. 跑共用性探测（上面命令），判定 solo/shared-*。
3. 运行时预检：`bash scripts/bootstrap.sh --check-only`。
4. 环境状态：`dotf status`（只读 L0，需 `--yes` 由 dotf 自动加；只读不装不配）。
5. 输出：OS、共用性判定、缺失的运行时、当前已装/未装的关键模块，并给出 **profile 推荐**。
6. 不创建台账（除非用户明确要求）；不改任何系统状态。

### plan

1. 基于推荐 profile（或用户指定），跑 `dotf init --profile <name> --dry-run`。
2. 把计划里涉及**系统级动作**的行高亮提醒（sudo / chsh / docker / 改 /etc）。
3. shared 场景下，明确指出哪些动作会影响其他用户，询问是否：
   - 换更小的 profile
   - 跳过某些模块（用户后续可用 `dotf-install` 单独装用户级的）
   - 仍要执行（记录到台账的 chsh/系统级决策）

### run

实际初始化。顺序：

1. **先确认共用性与 profile**（check/plan 的结论）；shared 下若用户要装 system 或 chsh，已在 plan 阶段确认过。
2. **bootstrap 运行时**：
   ```bash
   # 缺基础依赖（bash/git/curl/python3/PyYAML）时补齐；仅缺 PyYAML 会无感 pip --user 装
   bash scripts/bootstrap.sh             # 交互，缺依赖会问
   bash scripts/bootstrap.sh --yes       # 非交互自动补
   ```
   bootstrap 完成后会自动 `exec dotf init`。若想分开跑，用 `--check-only` 后自行调用 dotf。
3. **dotf init**（如 bootstrap 未自动委托，或要换 profile/参数）：
   ```bash
   dotf init --profile <name>            # 交互，会确认计划
   dotf init --profile <name> --yes      # 非交互（仍保留 chsh/docker 副作用确认）
   dotf init --profile <name> --dry-run  # 先看计划
   ```
4. **shared 下 chsh 处理**：若 zsh 在计划里且会触发 chsh，在 dotf 的副作用确认处，提示用户级绕过方案；用户选择不改 shell 时，配置文件仍会就位，登录后 `exec zsh` 即可用。
5. **完成后回写台账**：profile、已初始化模块、chsh 决策、踩坑。

### ledger

单独读写 `~/.dotf-env.md`：
- `ledger show`：打印台账内容。
- `ledger update`：重新探测并更新（不改系统状态）。
- 用户主动要求「记一下这台机器」「更新台账」时进入。

## 常见交互

| 用户说 | 行为 |
|--------|------|
| 「初始化这台机器」「setup 新机」 | check → 给推荐 → plan → 用户拍板 → run |
| 「这是公司机/共用机」 | 直接按 shared-user/shared-home 处理，默认 minimal，强调不 chsh |
| 「先看看要装啥」 | check + plan（全 dry-run） |
| 「用 remote profile」 | run --profile remote（仍先 dry-run 确认） |
| 「不要 chsh」 | 记录到台账，zsh 配置照装，给 exec 方案 |
| 「装个 nvim 就行」 | **改用 dotf-install skill**，不走 init |

## 安全与边界

- **绝不**在 shared 场景下未经确认 sudo、改 /etc、chsh、加 docker 组。
- **绝不**覆盖他人 HOME 下的同名配置而不备份——`dotf` 的 config 已有备份机制，但 shared-home 下要格外提醒。
- 需要 sudo 的命令一律走 `dotf`/`bootstrap.sh` 已有的确认流程，skill 层不要自己拼 sudo。
- 探测命令只读；若某探测命令需要权限，换只读替代或跳过，不要为此 sudo。
- 台账 `~/.dotf-env.md` 禁止写入密钥/token/密码明文。
- 脚本若失败或行为与 skill 描述不符：记录到台账踩坑节，并提示用户「可能需要更新 dotf 脚本或本 skill」——保持脚本与 skill 的兼容性反馈闭环。
