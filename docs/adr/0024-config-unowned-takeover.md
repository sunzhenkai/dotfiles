# Config 部署补 Takeover 出口：与 skills 同一套 `--takeover=backup` / `/dev/tty` 确认语义

`dotf <module> -c` 的 plan/apply（`src/dotf_core/config_deploy.py`）对 Unowned Target 一直 fail closed：目标路径已有常规文件、内容与受管版本不等价、config-manifest 无 `config:<module>` 所有权 → `unowned-real-target` 冲突，apply 拒写。这在语义上是对的（ADR-0019/0020 对 skills 已经这么定），但 skills 侧有 `--takeover=backup` 出口、config 侧没有：新机器上工具运行时先写了配置（例如 pi 启动即回写 `~/.pi/agent/settings.json`），之后 `dotf pi -c` 永远卡死，只能手删文件让路——而"手删再跑"恰恰绕开了本该做的备份与所有权登记。skills 与 config 同属一套 Unowned Target 词条，出口却只有一半，是词条级的不一致。

决定：

1. **复用既有策略参数，不发明新机制**：`compile_config_plan` / `deploy_config` 增加 `on_takeover: "skip" | "backup"`（默认 `"skip"`，行为与旧版逐字节一致）。`backup` 分支只改判"常规文件 + 无所有权 + 内容不等价"这一种状态为 `update`，写路径完全复用 `atomic_write(backup_root=...)`——旧字节进 `${XDG_STATE_HOME:-~/.local/state}/dotf/backups/<run-id>/`，所有权在同一 plan/apply 事务里首次登记。与 skills 共享 `DOTF_TAKEOVER` 环境变量（`--takeover=backup` 经 `Ctx.export()` 已经会导出，config 侧只是开始消费它）。
2. **确认交互照抄 skills 的形状**：`config_handler.decide_takeover` —— 显式 env 直接生效不询问；无冲突不询问；T​​TY 上先用 `backup` 策略编译一遍、用 `takeover_targets()` 枚举**真正可接管**的目标做一次汇总确认，提示写到 `/dev/tty`（Executor 捕获 handler stdout，`stdout.isatty()` 恒假）；默认 N。一次确认覆盖该模块本次计划的全部可接管项。
3. **不可接管的照旧 fail closed**：symlink、类型不符（该放文件处是目录）、foreign owner 等冲突不在 `takeover_targets()` 集合内，带 `--takeover=backup` 也不会被解除；确认时若候选集为空则不弹问题直接失败。
4. **规划后防线**：takeover 操作在 apply 的 `_assert_operation_fresh` 里 pin 规划时字节哈希——规划到应用之间文件再被改动则拒绝，与既有 freshness 检查同级。

否决的替代方案：
- *让 config 走 `--on-conflict=backup`*：违背 ADR-0019/0020 已确立的 Conflict/Takeover 分家（"修补已受管漂移" ≠ "首次吞并外来文件"），会混淆两个词条。
- *删除冲突文件重跑*：绕过备份与所有权登记，且要求用户理解 manifest 内部状态。
- *config 侧独立新 flag*：同一台机器上 skills 与 config 对同一种状态给两个开关，词条与 `DOTF_TAKEOVER` 语义碎裂。

后果：`dotf pi -c` 这类"新机先被工具写过"的场景在 TTY 下多一次确认即可完成接管；脚本/CI 必须显式 `--takeover=backup`（非 TTY 永不自动接管）。`tests/test_config_takeover.py` 固化默认 fail closed、backup 链路、边界（symlink/目录不可接管、规划后变更拒绝）与 handler 的四种决策路径。
