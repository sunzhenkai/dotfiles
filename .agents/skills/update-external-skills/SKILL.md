---
name: update-external-skills
description: "更新编目里已有第三方（外部）skill 的上游 revision 并下发本机：make skills-lock-update 重锁+逐 skill 审计 → 看 content_hash 判断内容是否真变 → registry validate → bin/dotf agents -c --yes 同步 → 对内容有变的 skill 按上游 checkout 验证。在用户要求更新外部/第三方 skill、刷新 revision、重锁 skills.lock、同步 skill 上游时使用。一手 skill 的修改走 pwd-skill-manager；新装/移除第三方 skill 走 skills-store 或直接改 skills.yaml 编目——本 skill 只刷新已有条目的 revision。"
---

# update-external-skills

把 `agents/skills.yaml` 编目里第三方 group 的锁（`agents/skills.lock.yaml`）推进到各 source 当前 HEAD，审计通过后下发本机。四步走完即完成，验证步只对内容真变的 skill 做。

## 流程

### 1. 重锁（仓库优先）

```bash
make skills-lock-update
```

- 对每个 source：fetch HEAD → 逐 skill 跑 `agents/skills/skills-store/scripts/audit-skill.sh` → 审计通过才写 lock；audit date 与 evidence 链接同步刷新。
- 完成标准：输出末尾 `wrote agents/skills.lock.yaml sources=N blocked=0`。N 只数有推进的 source（已最新的显示 `current`，不计入）。
- 默认警告也接受写入（fail-open）；要 fail closed 用 `FAIL_ON_WARN=1 make skills-lock-update`。

### 2. 判断内容是否真变

```bash
git diff agents/skills.lock.yaml | grep -E '^[+-].*content_hash'
```

revision / evidence / audit date 必然刷新，**content_hash 才是内容变化的信号**。没有 content_hash 变化就是纯重钉（上游只动了锁外文件，如 README、in-progress/），第 4 步可跳过。

### 3. 校验并下发本机

```bash
make registry validate
bin/dotf agents -c --yes
```

`agents -c` 输出分段解读（每段各管一摊，别看错行）：

| 段 | 管什么 | 本次该看什么 |
|----|--------|--------------|
| `instructions` | 全局指令 4 个安装产物 | `changed=0` 即无漂移 |
| `skills`（×各 agent） | 一手 + 渲染编目 skill | 第三方 skill **不在这里** |
| `defaults`（×各 layout） | **锁内第三方 skill**，按 lock revision 网络取回部署 | 第三方是否更新看这行的 changed |
| `openspec skills` | OpenSpec 全局 skills | CLI 缺失会 warning 跳过，与本流程无关 |

### 4. 验证（仅 content_hash 有变的 skill）

安装副本不是上游字节树（见坑 5），不能拿 lock 的 content_hash 直接对安装目录算哈希。正确做法：自己取上游、checkout 到 lock 里写的 revision，再比对。

```bash
git clone --quiet --filter=blob:none <source> /tmp/verify-skill
git -C /tmp/verify-skill checkout --quiet <lock 里的 revision>

# 字节级：上游 checkout 应精确等于 lock 的 content_hash
python3 -c "import sys; sys.path.insert(0, 'src'); \
from pathlib import Path; from agents.third_party import tree_hash; \
print(tree_hash(Path('/tmp/verify-skill/<subdirectory>')))"

# 落地级：安装副本与上游内容一致（三个 layout：~/.agents、~/.claude、~/.kiro 的 skills/<id>）
diff -r /tmp/verify-skill/<subdirectory> ~/.agents/skills/<id>
```

`diff -r` 允许的差异只有「Only in /tmp/verify-skill/...」的 authoring 目录：`patches/`、`evals/`、`experience/`、`evolutions/`、`authoring/`（见坑 5）。其余任何差异都说明下发没到位，回查 `defaults` 段输出。

## 坑实录（2026-09-20 实战沉淀）

1. **`dotf` 不在非交互 shell 的 PATH**：agent 会话里直接敲 `dotf` 得到 `command not found`。用仓库根 `bin/dotf`。
2. **非 TTY 环境必须 `--yes`**：任何 `dotf` 动作在无 TTY 下不带 `--yes`/`--dry-run` 都会报 `/dev/tty: No such device` 快速失败。预览用 `--dry-run`，执行用 `--yes`。
3. **`skills` 行 `changed=0` ≠ 第三方没更新**：锁内第三方 skill 走 `defaults` 段，`skills` 段只管一手 skill。只看 `skills` 行会误判「什么都没发生」。
4. **`defaults` 的 `changed=265` ≠ 265 个文件内容变了**：第三方安装身份内嵌整把锁的 digest（`src/agents/managed_runtime.py` 的 identity 注释），lock 任何变动都会让全部锁内 skill 重写一遍。changed 行数只说明「重写了」，内容是否变化回看第 2 步的 content_hash。
5. **安装副本对 lock 哈希必然 mismatch**：上游 skill 树带 authoring 目录（`patches/evals/experience/evolutions/authoring`），下发时被剥离（`_REQUIRED_EXCLUSIONS`）；一手 skill 还会按 agent 渲染 frontmatter。tree_hash 只用于验证上游 checkout，安装副本用 `diff -r` 验证。
6. **`/tmp/dotf-lock-update-*` 里的 checkout 别默认是新 HEAD**：临时目录里新旧 revision 的 checkout 都可能出现（本次拿旧基线当新上游，差点误诊）。比对一律自己 clone 并 checkout 到 lock 里写的 revision。
7. **`dotf agents -d`（doctor）是 L0 浅检**：只确认 managed manifest 就位，不验证 lock 内容一致性。真验证靠第 4 步，doctor 不能替代。
8. **mattpocock 重钉常是纯 revision 前进**：上游提交往往只动锁外路径（in-progress/、README），17 个锁内 skill 内容零变化。重锁后 diff 里只有 revision 行在动属正常，别当成失败。

## 边界

- **只刷新已有第三方条目**。新装/移除第三方 skill、改编目（增删 group 或成员）需要新审计锁，走 skills-store / `dotf skills add` / 直接编辑 `agents/skills.yaml`，不在本流程。
- **一手 skill 的修改走 pwd-skill-manager**（或直接改 `agents/skills/<id>/`），与本流程无交集。
- lock 变更是数据变更，收尾提交遵循仓库惯例（`agents: ...` 风格），提交前 `make registry validate` 必须先过。
