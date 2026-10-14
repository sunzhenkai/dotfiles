---
name: update-external-skills
description: "更新编目里已有第三方（外部）skill 的上游 revision：make skills-lock-update 重锁+逐 skill 审计 → lock_verify changed 判断内容是否真变 → registry validate 校验仓库产物，到此为止。下发本机（bin/dotf agents -c）与提交/推送不在流程内，作为下一步提示交给用户。在用户要求更新外部/第三方 skill、刷新 revision、重锁 skills.lock、同步 skill 上游时使用。共享 skill 的修改去 `sunzhenkai/solo-skills` 仓；新装/移除第三方 skill 走 skills-store 或直接改 skills.yaml 编目——本 skill 只刷新已有条目的 revision。"
---

# update-external-skills

把 `agents/skills.yaml` 编目里第三方 group 的锁（`agents/skills.lock.yaml`）推进到各 source 当前 HEAD，判定哪些条目内容真变，校验仓库产物自洽。**交付物就是一份审计过、变化已判定的 lock diff**。

三步走完即完成。下发本机与提交/推送是**后果与授权面不同的下一步**，默认只给提示、不执行（见「收尾」）。

第 2 步的分类判读是确定性的，已编码进 `src/agents/lock_verify.py`（`make skills-verify`），agent 只看结论与 `FAIL` 行。

## 流程

### 1. 重锁（仓库优先）

```bash
make skills-lock-update
```

- 对每个 source：fetch HEAD → 逐 skill 跑审计脚本（`src/agents/lock_update.py` 的 `resolve_audit_script` 回退链：仓内 first-party 副本 → source checkout 自带的 `skills/skills-store/scripts/audit-skill.sh` → 本机受管副本 `~/.agents/skills/skills-store/scripts/audit-skill.sh`）→ 审计通过才写 lock；audit date 与 evidence 链接同步刷新。
- 完成标准：输出末尾 `wrote agents/skills.lock.yaml sources=N blocked=0`。N 只数有推进的 source（已最新的显示 `current`，不计入）。
- 默认警告也接受写入（fail-open）；要 fail closed 用 `FAIL_ON_WARN=1 make skills-lock-update`。
- 这是全流程唯一必经的网络成本，别在它前后加重复取上游的动作。

### 2. 判断内容是否真变（纯本地，不打网络）

```bash
python3 src/agents/lock_verify.py changed
```

对比 HEAD 与工作区的 lock，输出末尾：

```text
changed_content=N changed_revision_only=M added=A removed=R
```

revision / evidence / audit date 必然刷新，**content_hash 才是内容变化的信号**。`N=0` 就是纯重钉（上游只动了锁外文件，如 README、in-progress/），连下一步的下发都可以省。`added` / `removed` 非零说明条目集变了——上游改名或增删 skill，见坑 12：那是编目变更，要先改编目并给锁补种子条目。

**本步不做上游验证**：`tree_hash == content_hash` 的断言与逐 layout 落地核对长在同一个 `verify` 调用里，而 layout 核对要求本机已下发，因此它属于下一步（下发之后）。在没有子集入口的前提下提前跑，等于白取一遍上游（坑 4）。

代价要认：lock 里的 content_hash 由 `lock_update.py` 在自己的 checkout 上算出，属**写入方自报**；独立复验随 `verify` 一起挪到了下发之后。因此本流程单独走完时，锁的可信度停留在「审计脚本判过 + 哈希自报」。**采信来源不是自己审过的 revision 时（新 source、批量跳版本、他人提的锁改动），先走下一步完成下发与核对，再谈采信。**

### 3. 校验仓库产物

```bash
make registry validate
```

只校验编目/注册表自洽，秒级、无网络。过了就具备提交条件——**但提交本身交给你**（见「收尾」）。

## 收尾：默认不动本机，把授权动作说清楚

流程内**禁止**这三件事，无论多顺手：

- `bin/dotf agents -c --yes`（会覆写三个 agent home 下的安装产物）
- `git commit`
- `git push`

做完三步就停，向用户输出一份可直接执行的下一步清单，说明各自后果，由用户决定跑不跑。清单模板：

```bash
# 1. 下发本机（重取全部锁内条目并重写，实测分钟级；见坑 4）
bin/dotf agents -c --yes
# 2. 下发之后才有意义的核对：上游哈希 + 三个 layout 的已装副本
make skills-verify            # 只验内容真变/新增的条目
# 3. 提交（仓库惯例：agents: ... 风格；registry validate 已过）
git add agents/skills.lock.yaml && git commit
```

用户已经在本轮明确要求「下发/提交/推送」时，才在本流程内执行对应那一条，且只执行被点名的那条。

## 下一步：下发与核对（需授权）

```bash
bin/dotf agents -c --yes && make skills-verify
```

### 下发输出分段解读（每段各管一摊，别看错行）

| 段 | 管什么 | 本次该看什么 |
|----|--------|--------------|
| `instructions` | 全局指令 4 个安装产物 | `changed=0` 即无漂移 |
| `skills`（×各 agent） | 一手 + 渲染编目 skill | 第三方 skill **不在这里** |
| `defaults`（×各 layout） | **锁内第三方 skill**，按 lock revision 网络取回部署 | 第三方是否更新看这行的 changed |
| `openspec skills` | OpenSpec 全局 skills | CLI 缺失会 warning 跳过，与本流程无关 |

同步报 `error: agents sync 有阶段失败` 时，失败行本身就写着原因，别猜：`target exists without agents ownership` / `stale owned target was modified locally` 指某个 layout 里已有副本不归本轮计划覆写，最常见是 first-party 迁出后留在 `~/.agents/skills/` 的陈旧目录（坑 13）。备份改名再重跑，不要就地覆盖。

### 核对（`make skills-verify`）

```bash
make skills-verify                       # 验内容真变 + 新增的条目
make skills-verify ALL=1                 # 验锁内全部条目
make skills-verify IDS=a,b VERBOSE=1     # 指定条目 + 打印干净项
```

**同一轮只跑一次**：target 每次调用都重新取上游（按条目取，坑 4），想同时看逐 layout 明细就在同一次调用带 `VERBOSE=1`，不要先跑一遍再补跑 verbose 遍。

脚本做三件事，全部复用安装器自身的代码，不另立判读标准：

- 重新取上游并 checkout 到 lock 写的 revision（不碰 `/tmp/dotf-lock-update-*` 的残留 checkout，坑 6），逐条断言 `tree_hash == content_hash` 与 license hash。
- 期望的已装副本 = `managed_runtime.compile_skills_plan(..., include_unlisted=True)`，与 `defaults` 部署时同一个调用。所以「上游有、本机没有」不是差异，而是剥离：剥离面 = `policy.excluded` ∪ 点开头文件；frontmatter 与 `$ARGUMENTS` 的渲染差异由 `sync.renderers_for(layout)` 自动吸收。
- 出口标签：`missing <相对路径>` 该在而不在 / `content <路径>` 已装内容与锁不符 / `unowned <路径>` 盘上有、锁计划不拥有 / `NOT-INSTALLED` 条目在 Desired Set 之外（optional 或 overlay 停用，坑 9）/ `prunable` 托管副本已不该存在。运行残留（`__pycache__/`）不计。

`failures=0` 即完成。出现 `unowned` 时按坑 10 定性（多半是迁移前的陈旧副本），确认无价值再删——脚本不替你删。副本 `content` 成片报错，先确认下发跑过且成功，别判成上游问题。

兜底（脚本不可用时手工验）：安装副本不是上游字节树（坑 5），不能拿 content_hash 直接对安装目录算哈希。自己 clone、checkout 到 lock 的 revision，用 `tree_hash` 对上游树，用 `diff -r` 对安装副本；上游侧多出的 `patches/`、`evals/`、`experience/`、`evolutions/`、`authoring/`、`tests/` 之外的任何东西、以及 `~/.agents` / `~/.claude` 副本正文与上游不一致，才算漂移。

## 坑实录（自 2026-09-20 实战沉淀，2026-09-29 补 12–15）

坑 5 / 6 / 9 与下发失败定性已由 `src/agents/lock_verify.py` 自动分类，留在这里是为了脚本不可用时能手工复现，以及解释那些标签到底在说什么。

1. **`dotf` 不在非交互 shell 的 PATH**：agent 会话里直接敲 `dotf` 得到 `command not found`。用仓库根 `bin/dotf`。
2. **非 TTY 环境必须 `--yes`**：任何 `dotf` 动作在无 TTY 下不带 `--yes`/`--dry-run` 都会报 `/dev/tty: No such device` 快速失败。预览用 `--dry-run`，执行用 `--yes`。
3. **`skills` 行 `changed=0` ≠ 第三方没更新**：锁内第三方 skill 走 `defaults` 段，`skills` 段只管一手 skill。只看 `skills` 行会误判「什么都没发生」。
4. **一条锁变更 = 全量重取 + 全量重写，且无子集入口**：第三方安装身份内嵌整把锁的 digest（`src/agents/defaults.py` 的 `identity_prefix`），lock 任何变动都让全部锁内 skill 在三 layout 各重写一遍；`defaults` 又在算计划**之前**无条件 `acquire_all(全部 desired 条目)`，而 `acquire_all` 按**条目**逐个 `git fetch`（同仓 N 个 skill = N 次往返，staging 是 TemporaryDirectory，无跨轮缓存）。三重相乘使下发成为全流程最贵一步（一轮实测约 390s）。`only_ids` 只到 planner 层，CLI 没有 `--ids`/`--only-ids`——**别承诺「只同步有变的条目」**，也别为省时间提前跑 verify（它复用同一条按条目取回的路径）。changed 行数只说明「重写了」，内容是否变化回看第 2 步。
5. **安装副本对 lock 哈希必然 mismatch**：上游 skill 树带 authoring 目录（`patches/evals/experience/evolutions/authoring`），下发时被剥离（`_REQUIRED_EXCLUSIONS`）；一手 skill 还会按 agent 渲染 frontmatter。tree_hash 只用于验证上游 checkout，安装副本用 `diff -r` 验证。
6. **`/tmp/dotf-lock-update-*` 里的 checkout 别默认是新 HEAD**：临时目录里新旧 revision 的 checkout 都可能出现（本次拿旧基线当新上游，差点误诊）。比对一律自己 clone 并 checkout 到 lock 里写的 revision。
7. **`dotf agents -d`（doctor）是 L0 浅检**：只确认 managed manifest 就位，不验证 lock 内容一致性。真验证靠下发后的 `make skills-verify`，doctor 不能替代。
8. **mattpocock 重钉常是纯 revision 前进**：上游提交往往只动锁外路径（in-progress/、README），17 个锁内 skill 内容零变化。重锁后 diff 里只有 revision 行在动属正常，别当成失败。
9. **`optional: true` 的锁内条目本机没有副本，不是下发失败**：编目里标 optional 的第三方条目不进默认安装，`defaults` 段也不部署（本机经 overlay / `agents apply` 启用过的才会有，如 ui-skills-root）。核对时它们只验上游 checkout 的 tree_hash == lock content_hash，`diff -r` 会报 MISSING，属预期。
10. **optional 条目在本机有非托管副本时，`diff -r` 对不上不是下发失败**：坑 9 说的是 optional 默认没有副本；若它**恰好存在**且内容对不上，多半是更早手工拷贝的陈旧副本，本流程不负责刷新，别顺手覆盖。四个信号一起看才能定性：副本里带着 `patches/`、`evals/` 等本应被剥离的 authoring 目录（锁定部署不会留下它们）；`~/.local/state/dotf/agents-manifest.json` 里查无此 id（`defaults` 段没部署过）；与**旧** revision 的 diff 行数明显少于与新 revision 的（说明血缘更老，不是"同步失败"）；副本 mtime 早于本轮更新。定性后按 optional 条目只验上游 `tree_hash == content_hash` 即可落地级收尾。是否刷新这类副本是独立决策——它们可能有意保留着上游后来重建掉的内容。实例（2026-09-28）：`ui-template-apply` / `ui-template-author` / `ui-template-design` 在 `~/.agents/skills/` 下正是这种副本，而 `archify` / `senv-cli` 无副本。
11. **审计误报挡 lock 前进时，改审计规则要走 skills-store 的更新流程（源在 solo-skills 仓）**：`jailbreak_role` 命中 MIT LICENSE 套话（`without limitation`）曾让 archify 每轮重锁都要人工豁免。这类「过宽 token」精度修复改 `sunzhenkai/solo-skills` 仓的 `skills/skills-store/`（脚本 + `tests/test_audit_skill.py` 本仓侧回归 + 该仓 `skills/skills-store/patches/` 留 proposal/change/result 三件套），提交推送后重锁到新 revision；**安装当场**不得改脚本，也不得为放行某个 skill 删规则。skills-store 自身的自指文本（规则表、误报表）用其 `.audit-allow` 豁免，不走规则放宽。
12. **上游改名条目：编目改了还不够，重锁读的是锁**。`lock_update.py` 按 `skills.lock.yaml` 现有条目逐个 promote，条目在新 HEAD 缺子目录就硬失败（`error: <id>: subdirectory missing at <rev>`），改名/增删因此永远解不开阻塞。做法：编目改名的同时给锁补种子条目（删旧 id、按同一 source/revision 写新 id），再 `make skills-lock-update`——`_promote` 会重算 content_hash、license hash 与 evidence，种子值随即被覆盖。两个坑：种子的 content_hash 别写全 0，YAML 会把 `000…0` 读成整数 `0`，load_lock 直接报 `content_hash must be a non-empty string`，用 `"a"*64` 这类非零占位；audit.evidence 必须是 https URL，随便写个词过不了 load_lock。`changed` 报告会把改名显示成 `added` + `removed` 一对。
13. **first-party 迁出后，`~/.agents/skills/` 里的旧副本会挡住锁定部署**：迁出只搬仓库里的源，`defaults` 段要在共享 layout 装同名 skill 时才发现目标已有副本且身份不匹配，于是 `skills` 段报 stale owned、`defaults` 段报 without ownership，整个 sync 失败而 `~/.claude` / `~/.kiro` 已装好。先比对再处置：runtime bundle 由 `agents/runtime.yaml` 的 `excluded` ∪ 点开头文件决定，副本里多出的 `patches/`、`evolutions/` 等在上游 revision 里通常都有——`make skills-verify IDS=<id>` 的 `unowned` 行就是这些差异。备份改名到 skills 树之外（`~/.agents/stale-backups/`）后重跑 sync；留在 skills 树里即使是点开头也会被 agent 运行时扫出来当 skill。
14. **`lock_verify.py` 的取上游必须走模块级 `_acquire`**：`src/agents` 是无 `__init__.py` 的命名空间包，`agents.third_party` 与 `third_party` 是两个模块对象，异常类不同身份，`except ThirdPartyLockError` 会静默漏过。新代码跟同目录邻居一样用扁平 import（`src` 与 `src/agents` 双插 sys.path，只为 `ensure_pyyaml`），别写 `from agents.x import`。
15. **把下发/提交/推送当流程内步骤是自找的返工**：它们改的是本机安装产物与 git 历史，与「一份审计过的锁」这个交付物无关，却占了最贵的时间窗口和最不可逆的动作面。一轮真实执行里，未经要求的提交因把在制品和锁变更混进同一个 commit，又追加了一次 reset 重写历史的返工。判据：动作的授权来源必须是用户本轮的点名，不能是 skill 正文里「收尾遵循仓库惯例」这类含糊措辞。

## 边界

- **只刷新已有第三方条目**。新装/移除第三方 skill、改编目（增删 group 或成员）需要新审计锁，走 skills-store / `dotf skills add` / 直接编辑 `agents/skills.yaml`，不在本流程。
- **共享 skill 的修改去 `sunzhenkai/solo-skills` 仓**（原 first-party 集合已全部迁出，本仓以第三方 group 消费）；本仓项目级 skill（`.agents/skills/`）的修改走 pwd-skill-manager，与本流程无交集。
- **下发、提交、推送一律不在流程内执行**（见「收尾」）。用户要求本流程给结论时，交付物是 lock diff 与 `changed` 计数；`make registry validate` 通过只代表具备提交条件，不代表可以代提交。
- 想让下发变便宜是**仓库工具**的活，不在本 skill：`acquire_all` 按 source 去重取回、`dotf agents` 增加子集入口。改这两处走本仓常规改动流程，不要试图在 skill 正文里绕开。
