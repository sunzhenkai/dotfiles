---
name: dotf-check
description: "环境体检：跨模块聚合检查基础运行时、shell 环境、程序/模块（按能力域而非机械罗列）、agents/skills 生态健康、配置健康与安全隐患，给出分级结论与修复建议，询问后可委托 dotf-init/dotf-install 修复。在用户要求体检、检查环境、check、诊断整体、看看缺啥、健康检查、env audit 时使用。与 dotf status（逐模块被动 L0）的区别：本 skill 做整体聚合、能力视角、主动发现、修复闭环。"
---

# dotf-check

整体环境体检。把分散的检查（基础运行时、shell、各模块、agents 生态、配置健康）聚合成一份**按能力域分类、分级**的报告，而不是逐模块机械罗列几十个 pass/fail。发现缺失后询问用户，确认后委托 `dotf-init` / `dotf-install` 修复。

## 核心原则

1. **聚合优先，不机械罗列**：不要输出「nvim: fail / tmux: fail / zsh: pass / ...」五十行。按**能力域**归并：「编辑能力：缺 nvim 配置」「终端复用：tmux 就绪」「agent 生态：claude/cursor 就位，kiro 缺」。
2. **只读体检，修复需确认**：检查阶段不改任何状态；修复阶段询问用户后委托对应 skill，不自己拼 sudo / 装 / 改 /etc。
3. **多用户感知**：读 `~/.dotf-env.md` 拿共用性判定；shared 下修复建议默认走用户级。
4. **分级结论**：每项给 `✅ 就绪` / `⚠️ 部分缺` / `❌ 缺失` / `ℹ️ 提示`，让用户一眼看到优先级。

## 与其他 skill 的边界

| skill | 视角 | 粒度 | 行为 |
|-------|------|------|------|
| **dotf-check**（本 skill） | 整体环境 | 能力域聚合 | 主动发现 + 询问后修复 |
| dotf-init | 首次初始化 | profile 级 | bootstrap + dotf init |
| dotf-install | 单模块/补装 | 模块级 | dotf <mod> -i/-c |
| `dotf status` | 逐模块 L0 | 单模块 | 只读，被动 |

体检后若发现「整体没初始化」→ 引导 `dotf-init`；若发现「个别模块缺」→ 引导 `dotf-install`。

## 体检的四个维度

### 维度 1：基础运行时与 shell 环境

`bootstrap.sh --check-only` 覆盖的，但 `dotf status` 不覆盖。

```bash
# 运行时（bootstrap 已有逻辑，这里直接复用）
bash scripts/bootstrap.sh --check-only    # 检测 bash/git/curl|wget/python3/PyYAML

# shell 环境
echo "$SHELL"                             # 当前默认 shell
command -v zsh && zsh --version           # zsh 是否就位
[ -f ~/.zshrc ] && echo "zshrc ok"        # 配置是否就位
echo "$STARSHIP_CONFIG" || command -v starship  # 提示符

# PATH 健康性（sanity）
echo "$PATH" | tr ':' '\n'                # 看有没有重复、空段、不存在的目录
command -v mise && mise --version         # SDK 管理器就位与否
```

**聚合输出示例**：
```
基础运行时
  ✅ bash/git/curl/python3 就绪
  ⚠️ PyYAML 缺失（pip install --user PyYAML 可补）
  ✅ zsh 就位（5.8），默认 shell 已是 zsh
  ℹ️ PATH 含 ~/.local/bin，正常
```

### 维度 2：程序/模块按能力域聚合

这是**本 skill 的核心差异化**。先跑 `dotf status` 拿到逐模块 L0 结果，再按 **能力域** 而非 group 机械罗列。

```bash
# 拿原始逐模块状态（只读 L0）
dotf status --profile full                 # 当前 OS 全集的 L0
dotf status --profile minimal              # 或更小范围
```

**能力域映射**（把 modules.yaml 的 group 重组为用户能理解的能力）：

| 能力域 | 涵盖 group / 模块 | 检查重点 |
|--------|-------------------|----------|
| **Shell 与提示符** | shell (git/zsh/starship) | git 就位、zsh 配置软链、starship 就位 |
| **SDK 与语言** | core (sdk/golang) + tools 里语言相关 | mise 就位、go/python/node 版本、GOPATH |
| **编辑器** | editors (nvim/helix/zed) | 编辑器二进制 + 配置软链 |
| **终端复用** | multiplexers (tmux/zellij) | 二进制 + 配置 |
| **终端模拟器** | terminals (kitty/alacritty/wezterm/ghostty/iterm2) | 桌面环境才查；远程可跳过 |
| **Agent 生态** | agents (claude/cursor/kiro/...) | 见维度 3 |
| **CLI 工具** | tools (delta/grepom/senv/k9s/yazi/...) | 按用户实际用到的查 |
| **云 CLI** | tools (aws/gcp/aliyun/ossutil) | 按需，不强求全装 |
| **桌面/输入法** | desktop (hypr/fcitx5/fonts) | 仅桌面机；远程 skip |

**聚合规则**：
- 每个能力域给一个总体状态，不逐个模块列。
- 只在「部分缺」或「缺失」时展开具体缺什么。
- 全就绪的能力域一句话带过。
- 用户明显用不到的（如远程机查终端模拟器、个人机查云 CLI）标注 `ℹ️ 按需，跳过`，不算缺失。

**聚合输出示例**（远程 minimal 环境）：
```
能力域体检
  ✅ Shell 与提示符：git/zsh/starship 全就绪
  ✅ SDK 与语言：mise + go1.22 + python3.11 + node20 就绪
  ⚠️ 编辑器：nvim 就绪，helix/zed 未装（按需）
  ❌ 终端复用：tmux 配置软链损坏 → 建议 dotf tmux -c
  ✅ Agent 生态：claude/cursor/zcode 就位（见下）
  ℹ️ CLI 工具：delta 就绪；grepom/senv 按需未装
  ℹ️ 终端模拟器/桌面/云 CLI：远程环境，跳过
```

### 维度 3：agents/skills 生态健康

`dotf agents -d` 覆盖但需主动调起；本 skill 把它纳入整体体检。

```bash
# agents 诊断（L0 + 可选 L1）
dotf agents -d                            # L0：各 agent CLI 是否就位
dotf agents -d --deep --json              # 深度诊断（脱敏 JSON，含 skills/MCP 同步状态）

# skills 同步状态（仓库 vs 本机）
dotf agents -c --dry-run                  # 看哪些 skills/commands 需要同步
```

**检查项**：
- 各 agent CLI（claude/cursor/zcode/kiro/...）二进制是否在 PATH
- skills/commands 是否与仓库 `agents/skills/` 一致（sync 差异）
- MCP 配置是否就位（`agents/env/mcp`）
- 重点：本 skill 自己（dotf-check）及 dotf-init/dotf-install 是否已分发到本机

**聚合输出示例**：
```
Agent 生态
  ✅ claude-code / cursor / zcode CLI 就位
  ⚠️ kiro CLI 未安装（按需）
  ⚠️ skills 同步差异：dotf-check 未分发到 ~/.cursor/skills（dotf agents -c 可补）
  ✅ MCP 配置就位
```

### 维度 4：配置健康与安全隐患

L0 会查软链，但不查这些；本 skill 补齐。

**检查项与命令**（全部只读）：
```bash
# 损坏的软链（dangling symlinks）—— L0 单模块会查，这里全 HOME 扫一遍重点配置
find ~/.config ~/.zshrc ~/.tmux.conf ~/.config/nvim -maxdepth 2 -xtype l 2>/dev/null

# 旧备份堆积（dotf 备份机制产生的 .bak.TIMESTAMP）
find ~ -maxdepth 3 -name "*.bak.*" -mtime +30 2>/dev/null | head

# 台账维护状态
[ -f ~/.dotf-env.md ] && echo "ledger ok" || echo "ledger missing"

# 共用性（复用 dotf-init 的探测）
getent passwd | awk -F: '$3 >= 1000 && $3 < 65534 {print $1}' | wc -l

# 敏感信息泄漏（只查 dotfiles 仓库内的配置，不查业务代码）
# 警告：只报告「疑似」，不打印内容
git -C "$(dotf __path)" grep -lE "(api[_-]?key|secret|token|password)\s*[:=]" -- 'config/' 2>/dev/null | head
```

**安全检查边界**：
- **只报告「疑似存在敏感关键字」，绝不打印匹配到的行内容或文件内容**。
- 命中后提示用户自行复核，不自动改文件。
- 不扫描业务代码仓库，只扫 dotfiles 自身的 `config/`。

**聚合输出示例**：
```
配置健康
  ❌ 2 个损坏软链：~/.config/nvim (→ 仓库已删)、~/.tmux.conf (→ 路径变更)
  ℹ️ 发现 3 个 >30 天的 .bak 备份，可清理
  ⚠️ ~/.dotf-env.md 不存在（建议 dotf-init 记录环境）
  ✅ 未发现 dotfiles 配置内的明文密钥疑似项
  ℹ️ 共用性：shared-user（2 个真实账号），修复建议走用户级
```

## 体检流程

1. **读台账** `~/.dotf-env.md`（共用性、已装模块、历史踩坑）；不存在标注 `ℹ️ 建议初始化台账`。
2. **跑四个维度的只读检查**（命令见上）；并行执行无依赖的检查以加速。
3. **聚合输出**：按能力域归并，分级标注，给出修复建议（指向具体 skill / 命令）。
4. **询问修复**：列出可修复项，问用户「是否修复以下问题？」，按选择委托：
   - 整体未初始化 → `dotf-init` skill
   - 单模块缺失 → `dotf-install` skill / `dotf <mod> -ic`
   - 配置软链损坏 → `dotf <mod> -c`
   - skills 同步差异 → `dotf agents -c`
   - 旧备份堆积 → 列出路径让用户确认后清理（不自动删）
   - 台账缺失 → 提示 `dotf-init` 的 ledger phase
5. **修复后复检**：修复完成的相关项重新跑一遍确认状态翻转。
6. **回写台账**：把体检结论与修复记录追加到 `~/.dotf-env.md` 踩坑节（若有新发现）。

## 分级标注规范

| 标注 | 含义 | 是否需要修复 |
|------|------|--------------|
| ✅ 就绪 | 检查通过 | 否 |
| ⚠️ 部分缺 | 能力域内部分项缺失，但核心可用 | 按需 |
| ❌ 缺失/损坏 | 关键项缺失或配置损坏 | 建议修复 |
| ℹ️ 提示 | 非问题，但有信息价值（按需跳过、台账状态、共用性） | 否 |

## 输出原则

- **顶部给摘要**：一句话总体结论（如「基础就绪，agent 生态完整，3 处配置需修复」）。
- **按维度分节**，每节内按能力域聚合，不逐模块罗列。
- **修复建议可操作**：每条 ❌/⚠️ 都带「建议运行 xxx」。
- **不重复 dotf status 的原始输出**：用户要看原始数据可自行 `dotf status`，本 skill 只给聚合结论。
- **远程 vs 桌面自适应**：探测到无桌面（无 DISPLAY / SSH 会话）→ 终端模拟器/桌面/输入法标 `ℹ️ 跳过`，不算缺失。

## 常见交互

| 用户说 | 行为 |
|--------|------|
| 「体检一下」「检查环境」「看看缺啥」 | 全四维度体检 → 聚合报告 → 询问修复 |
| 「只查 agents」 | 只跑维度 3 |
| 「我配置是不是坏了」 | 侧重维度 4（软链/备份/隐患） |
| 「修一下」 | 按体检结论委托对应 skill 修复 |
| 「这台机器健康吗」 | 全维度 + 摘要结论 |

## 安全与边界

- **检查阶段严格只读**：不装、不卸、不改配置、不 chsh、不 sudo。
- **修复阶段必须询问**：列出修复项与影响，用户确认后才委托；shared 下系统级修复仍走 dotf-init/dotf-install 的门禁。
- **敏感信息只报告不打印**：密钥/token 检查命中后只说「疑似 N 处」，不输出内容。
- **不自动删除任何文件**：旧备份、损坏软链只列出路径，由用户决定。
- **不扫描业务代码仓库**：安全检查只覆盖 dotfiles 自身的 `config/`。
- 体检结论可回写台账，但**不把逐模块原始输出写进台账**（那是临时数据）；只写聚合结论与新踩坑。
- 脚本若行为与 skill 描述不符（如 dotf status 输出格式变化导致聚合失败）：记录踩坑，提示更新本 skill 的解析逻辑——保持脚本与 skill 兼容性闭环。
