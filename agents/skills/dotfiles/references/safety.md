# 共用性、系统级门禁与台账

所有会改系统状态的动作（install / config / init / 体检后修复）之前先过一遍这里。

## 一、共用性判定

目的：这台机器是不是「多个真人共用」或「HOME 被共用」，据此决定允不允许 sudo / chsh 这类全局动作。

```bash
# 1. 有多少个真实人类账号
getent passwd | awk -F: '$3 >= 1000 && $3 < 65534 {print $1}'   # Linux
dscl . list /Users UniqueID | awk '$2 >= 500 {print $1}'        # macOS

# 2. 当前账号是否共用账号典型名（dev / shared / deploy / build / team / guest）
echo "$USER"

# 3. 现在还有谁登录
who

# 4. HOME 是否共用或非标（/home/dev、/shared、/workspace）
echo "$HOME"

# 5. 是否容器 / 一次性环境
[ -f /.dockerenv ] && echo container
```

| 结论 | 触发条件 | 默认策略 |
|---|---|---|
| `solo` | 只有一个真实用户，HOME 私有 | 可 `full` / `remote`；系统级动作仍走 dotf 的副作用确认 |
| `shared-user` | 多个真实账号，当前 HOME 私有 | 默认 `minimal` + 用户级模块；系统级动作显式确认 |
| `shared-home` | HOME 共用，或 `$USER` 是共用账号名 | 默认 `minimal`；**禁止** chsh；系统级动作一律先问 |

判定模糊时取更保守的一档（solo 与 shared-user 分不清 → 当 shared-user），并把假设讲给用户。

## 二、系统级风险点

| 模块 | 风险动作 | shared 下处理 |
|---|---|---|
| `system` | `sudo apt/dnf/pacman install`、改软件源 | 默认跳过或显式确认，说明「改动全局，影响所有用户」 |
| `system`（docker） | `usermod -aG docker`、`systemctl enable --now docker` | 显式确认；docker 组等价 root |
| `zsh` | `chsh -s` 改默认 shell | shared 下默认拒绝，给下方绕过方案 |
| `homebrew` | 装到 `/opt/homebrew` / `/home/linuxbrew` | 确认安装路径与组权限 |
| `fonts` | 装到系统字体目录 | 改用用户级目录（`~/.local/share/fonts`、`~/Library/Fonts`） |
| `hypr` / `fcitx5` | 改桌面会话 / 输入法 | 桌面机才做，显式确认 |

shared 下通常可直接装的用户级模块：

```
sdk golang git starship（仅配置、不 chsh） delta grepom senv mdserve npm
ossutil aws aliyun gcp vcpkg d2 dws lark-cli
agents cursor opencode codex kimi-code pi omp zcode claude-code trae-cli
nvim helix tmux zellij herdr yazi k9s
```

## 三、chsh 绕过（不改默认 shell 也能用 zsh）

```bash
# A. ~/.bashrc 末尾自动切（仅当前用户、仅交互式）
[ -n "$PS1" ] && [ -x "$(command -v zsh)" ] && exec zsh -l

# B. 仅当前会话
exec zsh -l

# C. 终端模拟器里把启动命令设为 zsh
```

zsh 的配置走 `copy` 落到 HOME 下的真实用户目录，不 chsh 也能用；登录默认 shell 仍是原来的。仓库源变更后要重跑 `dotf zsh -c`。

## 四、台账 `~/.dotf-env.md`

固定放用户 HOME，不进任何仓库。

| 情况 | 行为 |
|---|---|
| 不存在 | 探测完成后问用户「是否记录这台机器？」，同意才按下面模板创建；`--dry-run` / 体检阶段不创建 |
| 已存在 | 每个 phase 开始先读；完成实质操作后自动更新，不必再问 |

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

写法：只记环境事实与决策（profile、共用性、chsh 取舍、踩坑）；不写密钥 / token / 密码；不记临时命令输出与 pid；踩坑要写到「下次照做能避开」的程度。
