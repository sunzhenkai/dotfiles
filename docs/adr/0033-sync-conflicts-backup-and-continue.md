# agents sync 冲突默认「先备份再继续」：备份即裁决

ADR-0019/0020 把冲突处理定为 fail-closed：owned 漂移默认报告并保留（`--on-conflict=backup` 只解除内容/mode 漂移），Unowned Target 默认跳过（TTY 下二次确认，非 TTY 需显式 `--takeover=backup`），identity 不符永远 fail closed。实测代价：一次重锁（lock digest 变化）叠加一处本机编辑，就让整个阶段以 `defaults（exit=1）` 失败，需要人工「备份改名再重跑」——而人工步骤本身绕开了 dotf 的备份与所有权登记。

机器的主人要的是：**不失败，有冲突就备份继续**。

决定：

1. **默认「先备份再继续」，备份即裁决。** owned 漂移（内容 / mode / identity）与内容不等价的 Unowned Target 一律：先把当前字节备份到 `${XDG_STATE_HOME:-~/.local/state}/dotf/backups/<run-id>/`，再写入受管内容并继续。owned 漂移复用 `atomic_write(backup_root=...)`；stale 且被本机修改的项备份后 prune（`backup_target(..., remove_source=True)`）；Takeover 复用既有 update 路径并首次登记 ownership。identity 迁移不再需要人工介入：字节 pristine 或已等于新内容时沿用原有自动重登记，其余按普通漂移处理（备份 + 覆写 + 重登记）。
2. **取消确认交互。** Takeover 不再有 TTY 二次确认（`decide_takeover` / `--decide-takeover` 删除）：默认即 `backup`，`--takeover=skip` 显式收紧。config 部署（ADR-0024）不在本次范围，维持默认 skip + TTY 确认。
3. **`block` / `skip` 保留为严格回退。** `--on-conflict=block`：owned 漂移报告并保留，整份 Skill 跳过；`--takeover=skip`：unowned 分歧保持冲突。`RESULT` 仅在显式严格模式冲突或下列硬错误时为 failed。
4. **硬错误仍 fail closed。** 不安全类型（symlink / 类型不符）、manifest 不可解析、越界 stale 目标不受任何策略影响——这些意味着 dotf 不知道自己在覆盖/删除什么。
5. **报告面不随默认漂移。** doctor、TUI Status/Conflicts 面板与 `lock_verify` 以严格策略（`block` / `skip`）编译：本地漂移与无主目标继续以 `conflict` / `unowned` 分类呈现，不因 sync 默认会补救而隐身。sync `--verbose` 对补救操作标注 `(overwrite, backup)` / `(remove, backup)`。

随之更新：`src/agents/managed_runtime.py`（默认策略、identity 漂移补救、stale 修改项备份后 prune）、`sync.py`（删除确认机制）、`desired_ops.py`、`openspec_skills.py`、`scripts/modules/agents/sync.sh`（删除 decide 步骤）、`doctor.py` / `dotf_tui/state.py` / `lock_verify.py`（严格编译）、`agents/README.md`、`docs/Dotfiles.md`、`docs/design/skill-catalog.md`、`CONTEXT.md` 与测试。

后果：常规 `dotf agents -c` 不再因漂移/接管失败，本机字节始终可从 run 级备份恢复；「哪些文件被覆写」从"事前确认"改为"事后可查"（备份目录 + verbose 流水）。
