# Config 部署的 owned 漂移默认「先备份再覆盖」，并给拒绝写入的报错附处理选项

ADR-0033 把 agents sync 的 Conflict（owned 漂移）改成默认先备份再继续，但明确把 config 部署排除在外；ADR-0024 只给 config 补了 Unowned Target 的 Takeover 出口。结果 `dotf <module> -c` 对「本模块上次写入、之后被本机改过」的文件没有任何出口：`managed-target-modified` 直接失败，`--on-conflict` 在 CLI 层能解析、也会导出 `DOTF_ON_CONFLICT`，但 `config_handler` 从不读取。用户只能手删目标再重跑——这恰好绕开了 dotf 的备份。

实测还暴露了一个源头问题：config 源目录里被 git 忽略的运行时产物会被 copy 当成配置一起托管。旧版 antigen 在 `config/shell/zsh/` 里留下的 `aliases.zsh.zwc` 就这样被部署出去：目标处 zsh 一重编译就漂移，而且 dotf 写过去的是旧字节码、mtime 又比 `.zsh` 新，zsh 会加载过期的别名。

决定：

1. **config 开始消费 `DOTF_ON_CONFLICT`，默认 `backup`。** `compile_config_plan` / `deploy_config` 增加 `on_conflict: "block" | "backup"`（库默认 `block`，供 doctor 一类只读报告面使用）；`config_handler` 从环境读取，未设置时为 `backup`，与 agents sync 的默认一致。`backup` 只改判「常规文件 + 本模块 owned + 内容既不等于上次写入也不等于新内容」这一种状态为 update，写路径复用 `atomic_write(backup_root=...)`，旧字节进 `~/.local/state/dotf/backups/<run-id>/`。规划后文件再被改动时，apply 的 freshness 检查照旧拒绝。
2. **事后可查，不再事前确认。** 被覆盖的文件以一行 `warning:` 汇总输出（`target → backup`），经 `handler_common.sh` 拼进结果行，TTY 与 `last-run.json` 都能看到。`--on-conflict=block` 恢复旧行为：保留本机改动，该模块 config 动作失败。
3. **Takeover 不变。** 无主且内容不等价的文件仍按 ADR-0024 处理（默认 skip + TTY 确认，或显式 `--takeover=backup`）；`--on-conflict` 不解除它，两个词条继续分家。
4. **拒绝写入时附处理选项。** 冲突报错末尾追加去重后的「可选处理」：owned 漂移提示 `--on-conflict=backup`，可接管的无主常规文件提示 `--takeover=backup`，他模块所有提示调整 `modules.yaml`，其余（符号链接、该放文件处是目录等）提示确认无用后手动移走。
5. **运行时产物用显式 exclude 排除。** `preserve` / `exclude` 规则含 `*?[` 时按 fnmatch 匹配整条相对路径（`*` 可跨目录），否则仍是路径前缀；registry 的重叠校验同步认识 glob。zsh 模块声明 `exclude: ["*.zwc"]`。原先已被托管的 `.zwc` 在下一次部署时随 stale 处理直接解除托管，文件原样保留。

否决的替代方案：
- *TTY 下对 owned 漂移二次确认*：ADR-0033 已证明确认交互在多模块、非 TTY 场景里只会变成失败；备份已经保证可回滚。
- *扫描源目录时遵循 `.gitignore`*：最贴近「仓库即配置」，但会改变 nvim 等模块对已部署的被忽略文件（如 `lazy-lock.json`）的处理，进而触发 prune；影响面超出本次。
- *在扫描器里内置 `*.zwc` 忽略表*：隐式规则，不如在模块声明里可审计。

后果：常规 `dotf <module> -c` 不再因本机改过受管文件而失败，被覆盖内容总能从 run 级备份恢复；需要保留本机改动的用户要显式加 `--on-conflict=block`。`tests/test_config_drift_backup.py` 固化默认拒绝（库层）、backup 链路、规划后变更拒绝、Takeover 不受影响、报错提示、glob exclude 与 handler 端到端行为。
