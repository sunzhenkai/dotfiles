# 首次初始化（init）

把裸机或新用户账号带到一个可用 profile。判断与多用户风险在本节做，执行一律委托 `scripts/bootstrap.sh` 与 `bin/dotf init`。

## 什么时候用本节

- 「初始化新机」「setup 这台机器」「bootstrap」「装机」「配新开发环境」→ 本节
- 「装个 xx」「配一下 xx」「补装」→ 改用 `references/install.md`，不要走 init 全流程

## 真相源

| 文件 | 作用 |
|---|---|
| `modules.yaml` | 模块能力与路径（install / config / doctor / os / depends_on / group） |
| `profiles.yaml` | 使用场景 profile（minimal / remote / desktop / full） |

OS 检测、profile 展开、依赖拓扑都由 `dotf` 自己读这两个文件完成，不要在对话里维护模块清单。

```bash
dotf init --list        # OS profile + 使用场景 profile
```

在仓库根查全量模块（含 group / depends_on）：

```bash
PYTHONPATH=src python3 -m dotf_core.registry list --filter-os
```

## profile 推荐矩阵

先按 `references/safety.md` 判定共用性，再选 profile。

| 场景 | 共用性 | 推荐 | 说明 |
|---|---|---|---|
| 个人桌面 | solo | `full` | 当前 OS 适用全集 |
| 个人远程 / 服务器 | solo | `remote` | minimal + golang/nvim/tmux/herdr/delta/grepom/agents |
| 公司开发机（独占账号） | shared-user | `minimal` 起步，按需加用户级模块 | 不装 system 系统包，不 chsh |
| 公司共用账号 / 共用 HOME | shared-home | `minimal` | 仅用户级，绝不 chsh |
| 只想先看看 | 任意 | 先 `--dry-run` | 不改任何状态 |

`minimal` = system + sdk + git + zsh + starship。注意：**即便 minimal 也含 `system`（会 sudo 装系统包）和 `zsh`（可能 chsh）**，shared 场景要把这两点讲清楚，并准备好 `references/safety.md` 的绕过方案。

## Phases

用户意图决定 phase；识别不清缺省 `check`。

### check（只读）

1. 读 `~/.dotf-env.md`（若有）。
2. 跑共用性探测，得出 solo / shared-*。
3. 运行时预检：在仓库根 `bash scripts/bootstrap.sh --check-only`。
4. 环境状态：`dotf status`（只读 L0）。
5. 输出：OS、共用性判定、缺失运行时、关键模块已装/未装、**profile 推荐**。
6. 不创建台账、不改任何状态。

### plan

1. 预览：`dotf init --profile <name> --dry-run`（例：`dotf init --profile remote --dry-run`）。
2. 把计划里的系统级动作（sudo / chsh / docker / 改 `/etc`）挑出来讲。
3. shared 下问用户：换更小的 profile、跳过某模块（后续用 install 单独补用户级）、还是照装并记进台账。

### run

1. 确认共用性与 profile（check / plan 的结论）。用户拒绝 chsh 的，记进台账。
2. 补齐运行时：

   ```bash
   bash scripts/bootstrap.sh            # 交互，缺依赖会问
   bash scripts/bootstrap.sh --yes      # 非交互（仍保留 dotf 的副作用确认）
   bash scripts/bootstrap.sh --check-only
   ```

   bootstrap 依赖齐全后会自己 `exec dotf init`；想分开跑就 `--check-only` 后自己调。

3. 初始化：

   ```bash
   dotf init --profile <name> --dry-run     # 先看计划
   dotf init --profile <name>               # 交互确认
   dotf init --profile <name> --yes         # 非交互（chsh / docker 仍单独确认）
   ```

4. shared 下的 chsh：在 dotf 的副作用确认处选「否」，配置文件照装，登录后 `exec zsh` 即可；绕过方案见 `references/safety.md`。
5. 回写台账：profile、已初始化模块、chsh 决策、踩坑。

### ledger

单独读写 `~/.dotf-env.md`：`ledger show` 打印，`ledger update` 重新探测并更新（不改系统状态）。用户说「记一下这台机器」「更新台账」时进这个 phase。模板与写入门禁见 `references/safety.md`。

## 常见交互

| 用户说 | 行为 |
|---|---|
| 「初始化这台机器」「setup 新机」 | check → 给推荐 → plan → 用户拍板 → run |
| 「这是公司机 / 共用机」 | 按 shared-user / shared-home 处理，默认 minimal，强调不 chsh |
| 「先看看要装啥」 | check + plan，全 dry-run |
| 「用 remote profile」 | run --profile remote（仍先 dry-run） |
| 「不要 chsh」 | 记台账，zsh 配置照装，给 exec 方案 |
| 「装个 nvim 就行」 | 转 `references/install.md` |

## 边界

- 绝不在 shared 下未经确认 sudo、改 `/etc`、chsh、加 docker 组；需要 sudo 的一律走 dotf / bootstrap 的确认流程，不自己拼。
- 探测命令只读；某条需要权限就换只读替代或跳过，不为此提权。
- 脚本行为与本节描述不符（如某个「用户级」模块实际 sudo 了）：记进台账踩坑，并提示可能需要更新 dotf 脚本或本节内容。
