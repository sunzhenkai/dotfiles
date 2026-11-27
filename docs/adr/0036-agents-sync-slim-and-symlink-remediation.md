# agents sync 架构瘦身与根目录内软链默认解链

> **状态（2026-11-27）**：取代 ADR-0033 中把所有软链与热缓存当成高对抗多租户环境处理的实现细节，保留「先备份再继续」和根目录边界安全语义。

## 背景

`agents` 同步的核心职责只是把仓库内 first-party skill、lock 固定的第三方 skill、OpenSpec skills 和全局 `AGENTS.md` 同步到 `~/.agents` 与 `~/.claude` 等受管目录。此前实现叠加了过重的防 TOCTOU / 重复键 / 三遍读盘哈希 / 缓存二次校验 / per-entry identity 后缀 / 5 层 bash+Python 文本过滤，导致：

1. `~/.claude/skills/<id> -> ../../.agents/skills/<id>`（`npx skills` 标准布局）被判为 `unsafe` 且错报为 unowned，直接以 `defaults（exit=1）` 卡死；
2. 4 层管道（`defaults.py` → `sync.sh` → `config.sh` → `progress.py`/`run_plan.sh`）逐层吞掉错误明细，quiet 模式下 `run_plan.sh` 删除 `$out` 前未回放尾部，用户只看到 `agents sync 有阶段失败: defaults（exit=1）`；
3. 热缓存命中仍每次跑 `git rev-parse`/`sparse-checkout`/`checkout` + 重复 `LICENSE` 与 `/tmp` 二次 `tree_hash`；monorepo 更新 `revision` 时即使用 `content_hash` 未变也触发大量无意义重写；锁内外与 `_apply_operations` 对未变更文件重复 3 次 SHA-256。

## 决定

1. **区分根目录边界软链与根目录内软链**：
   - `home` 到 `target_root`（含 `target_root` 本身，如 `~/.agents/skills -> outside`）的软链、越界路径与非常规文件保持 `unsafe` 并永远 fail-closed。
   - 严格位于 `target_root` 之下的软链归类为 `actual_state="symlink"`（理由 `SYMLINK_CONFLICT`）；在默认 `backup` 策略下，只 `unlink` 软链本身（绝不跟随删目标）然后落盘受管副本；严格模式（`--on-conflict=block` / `--takeover=skip`）保留软链并报错。
2. **消除无意义的身份扰动与重复读盘**：
   - 移除 `entry_identity_suffixes` 与同 owner 下因 `source_identity` 移动导致的重写；纯 re-pin（`content_hash` 未变）不改写已安装目标。
   - `apply_owned_plan` 拿锁后若 manifest digest 未变则直接复用计划，不再二次编译；`none` 操作不再第三次读盘哈希；`adoptable_equivalent` 直接就地补记 manifest，不再先 `unlink` 再重写。
3. **热缓存零 `git`、直连验证目录**：
   - `third_party.resolve_locked_skills` 在缓存已物化时跳过全部 `git` 子进程，同仓 `LICENSE` 只校一次，`defaults` 直接从已校验缓存目录规划，不再经 `/tmp` `copytree` 与二次 `tree_hash`。
4. **单进程编排与失败回放**：
   - 新增 `src/agents/sync_all.py` 在单进程内编排 5 个阶段并透传精确失败原因；`scripts/modules/agents/sync.sh` 瘦身为薄包装；`scripts/run_plan.sh` 在 quiet 模式动作失败时回放清理后的日志尾部。

## 后果

- `npx skills` 遗留的跨 layout 软链在默认 `dotf agents -c` 下自动安全解链并接管，不再卡死，且软链指向的目标文件不受任何影响。
- 热缓存下幂等同步显著提速且不触发 git/重写；任何阶段失败都会把真实原因带到终端与 `last-run.json`。
