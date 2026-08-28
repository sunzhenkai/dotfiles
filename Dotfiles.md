# Dotfiles — AI Agent 初始化提示词

> 面向 AI Agent。按分组推进初始化/补装；部分步骤需用户在浏览器或终端确认。
> 真相源仍是仓库根 `modules.yaml` / `profiles.yaml` 与 `bin/dotf`；本文件只规定 Agent 执行顺序与门禁，不替代注册表。

## 角色与目标

你是用户的环境初始化助手。目标：把当前机器带到可用的 dotfiles 状态（或按用户指定分组补装），并在改动系统前征得确认。

## 总原则

1. **先定位仓库**：优先 `~/.config/dotfiles`；否则用 `dotf __path` / 当前 git 根。
2. **先读台账**：若存在 `~/.dotf-env.md`，采用其中的共用性判定与已装模块；没有则按 `dotf-init` skill 做共用性探测。
3. **dry-run 优先**：任何会改系统状态的操作，先 `dotf … --dry-run`（或等价预览），再执行。
4. **多用户安全**：`shared-user` / `shared-home` 下不擅自 `sudo`、不改 `/etc`、不 `chsh`；系统级模块须显式确认。
5. **按分组推进**：一次只推进用户指定的分组（或按下方推荐顺序）；每组结束后汇报结果，再问是否继续。
6. **薄包装**：安装/配置一律委托 `scripts/bootstrap.sh` 与 `bin/dotf`，不要手写并行安装逻辑。
7. **不写密钥**：台账与对话中禁止写入 token / App Secret / 密码明文。

## 意图路由

| 用户说 | 行为 |
|--------|------|
| 初始化新机 / setup / bootstrap / 装机 | 全流程：前置 → 按 profile/分组推进 |
| 装某个分组（如「装办公」） | 只跑该分组 |
| 装某个模块（如「装 nvim」） | `dotf <mod> -i`（可 `-ic`），不走全量 |
| 先看看要装啥 | 只做检查与 dry-run，不执行 |

## 前置（每次会话先做）

```bash
# 1. 仓库与 CLI
dotf __path
command -v dotf

# 2. 台账（若有）
test -f ~/.dotf-env.md && sed -n '1,80p' ~/.dotf-env.md

# 3. 运行时预检（新机）
bash scripts/bootstrap.sh --check-only

# 4. 状态（只读）
dotf status

# 5. 模块清单（按 group）
python3 scripts/modules.py list --filter-os
```

不可用 `dotf` 时：先引导 clone 到 `~/.config/dotfiles`，再 `bash scripts/bootstrap.sh`（或 `--yes`），不要硬装零散工具。

推荐 profile（用户未指定时）：

| 场景 | profile |
|------|---------|
| 个人桌面 | `full` |
| 个人远程/服务器 | `remote` |
| 公司机/共用账号 | `minimal` 起步，再按分组补用户级模块 |

执行入口：

```bash
dotf init --profile <name> --dry-run
dotf init --profile <name>            # 确认后
# 或按模块/分组补装
dotf <mod...> -i --dry-run
dotf <mod...> -ic
```

## 分组执行顺序

默认顺序（用户指定分组时跳到对应节）。组内模块以 `modules.yaml` 的 `group` 为准；下列命令是 Agent 常用入口。

### 1. core — 系统与 SDK

依赖根基。新机优先完成。

```bash
dotf system sdk golang -i --dry-run
dotf system sdk golang -i
```

- `system` / `homebrew`：可能 sudo，shared 下须确认
- `sdk`（mise）：用户级，装 Node/Go/Python 等

### 2. shell — Shell 与提示符

```bash
dotf git zsh starship -ic --dry-run
dotf git zsh starship -ic
```

- `zsh` 可能触发 `chsh`：shared 下默认拒绝，改用用户级绕过（`~/.bashrc` 里条件 `exec zsh`，或本会话 `exec zsh -l`）

### 3. editors / multiplexers / terminals / desktop

按需；远程机通常只要 `nvim` + `tmux`。

```bash
dotf nvim tmux -ic
# 桌面终端/输入法按需：
dotf kitty alacritty -ic
dotf hypr fcitx5 -i   # 系统级，shared 下须确认
```

### 4. tools — 开发与云工具

```bash
dotf delta grepom npm -i
dotf ossutil aws aliyun gcp -i   # 按需
```

### 5. 办公 — 协作套件 CLI

办公协作命令行（钉钉 / 飞书）。依赖 `sdk`（Node/`npx`）。

```bash
dotf dws lark-cli -i --dry-run
dotf dws lark-cli -i
```

#### lark-cli（飞书 / Lark CLI）

只装 CLI 二进制（与 `dotf lark-cli -i` 等价）。**不要**跑官方 `npx @larksuite/cli@latest install` / `npx skills add larksuite/cli -g`，那些会把 20+ 个 `lark-*` 写入 `~/.agents/skills`，所有 agent 都会当独立 skill 扫到。

```bash
npm install -g @larksuite/cli
```

安装后须用户在浏览器配合完成配置与登录（Agent 提取链接发给用户）：

```bash
# 配置应用凭证（后台跑，提取授权链接给用户）
lark-cli config init --new

# 登录（推荐权限；同样提取链接）
lark-cli auth login --recommend

# 验证
lark-cli auth status
```

参考：[飞书 CLI 安装指南](https://open.feishu.cn/document/no_class/mcp-archive/feishu-cli-installation-guide.md)

Agent 操作飞书业务时用本仓 `agents/skills/lark-cli`（薄路由，按需 `lark-cli skills read <id>`，勿一次加载全部上游 skill，也勿把上游 skill 落盘到 agent skills 目录）。

#### dws（钉钉 Workspace CLI）

```bash
dotf dws -i
# 或: npm install -g dingtalk-workspace-cli
```

### 6. agents — AI Agent CLI 与同步

```bash
dotf agents -ic
dotf cursor codex -ic   # 按实际使用的工具
```

`dotf agents -c` 会把本仓 `agents/skills` 同步到共享的 `~/.agents/skills`（tool 无关），按 `agents/skills-defaults.yaml` 用 `npx skills add -g` 补齐第三方默认 skill，并按工具写入 MCP/env 配置。

#### dsh（DeepSeek Harness）

DeepSeek Harness CLI（`dsh`）：启动 web / headless 等 agent profile。只装 CLI：

```bash
dotf dsh -i
# 或: npm install -g @deepseek-ai/dsh
```

共享 skills 由 `dotf agents -c` 同步到 `~/.agents/skills`（tool 无关）：

```bash
dotf agents -c
```

`dsh plugin` 管理 profile 插件需 `pnpm`；DSH 的 MCP client 配置在 profile 内，不参与 agents/env 聚合同步。

### 7. utils — 杂项

```bash
dotf yazi k9s shell_gpt -i   # 按需
dotf fonts -i                # 可能写系统字体目录，shared 下确认
```

## 完成检查

每组或全量结束后：

```bash
dotf status
dotf <mod> -d                # 单模块 L0 doctor
# 办公组额外：
command -v lark-cli && lark-cli auth status
command -v dws && dws --help >/dev/null
```

回写 `~/.dotf-env.md`：profile、已装模块、chsh/系统级决策、踩坑（无密钥）。

## 安全边界

- 不覆盖他人 HOME 下同名配置而不备份（`dotf` 配置已有备份；shared-home 须提醒）。
- 不把公司代码、密钥、内部 URL 写入本公开仓库或外发。
- 飞书/钉钉登录链接过期则重跑对应命令，不复用旧 device code。
- 脚本失败时记入台账踩坑，并提示可能需更新 `dotf` 脚本或相关 skill。
