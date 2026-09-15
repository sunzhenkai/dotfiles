# Skill sync：进度按 Layout 摘要；Takeover 逃离 ownership；冲突按 Skill 隔离

ADR-0019 把 `--on-conflict=backup` 限定为 owned 漂移出口，并让 Unowned Target 永远 fail closed。真实机器上大量 skill 来自 `npx skills` 或旧安装，sync 会刷屏逐文件日志，且同一 layout 内任一冲突整批 abort，一手失败还会挡住 defaults/OpenSpec。用户要的不是把 unowned 塞进 on-conflict，而是更好的进度面、可确认的接管，以及按 Skill 继续。

决定：

1. **进度**：默认每个 Skill Layout 一行进度与变更摘要（形如 `==> skills  shared  12↑ 3adopt 1✗ 2skip  |  180 files`）；冲突时追加失败 Skill id 名单。仅冲突文件明细或 `--verbose` 才落到 Skill/文件级流水。
2. **Takeover 与 Conflict 分家**：内容不等价的 Unowned Target 走 `--takeover=backup`（先 backup 再写入并登记 ownership）。`--on-conflict=backup` 仍只解除 owned 内容/mode 漂移。字节已等价的 unowned 继续静默 adopt，不进接管确认。
3. **确认**：TTY 在计划确认外对可接管项做一次全局汇总二次确认（写到 `/dev/tty`：Executor 会把 Handler stdout 接到管道，`stdout.isatty()` 为假，但 stdin 仍是终端）。非 TTY / 脚本必须显式 `--takeover=backup`（或 `DOTF_TAKEOVER=backup`），否则跳过这些 Skill。确认结果导出给一手 / defaults / OpenSpec 三个阶段共用。
4. **进度透出**：Executor 边跑边把 Handler 日志 tee 到终端（RESULT 行除外），不再等动作结束后整段回放。Python 子进程设 `PYTHONUNBUFFERED=1`，Layout 摘要才能即时出现。
5. **隔离**：同一 layout 内按 Skill 原子失败——任一文件 Conflict 或未接管的 Unowned Target 则该 Skill 整份不写，其它 Skill 继续。Layout 之间、以及一手 / defaults / OpenSpec 阶段之间成败相互独立；任一段失败仍使总 RESULT 为 failed，但不得跳过后续阶段。

拒绝把 Unowned Target 扩进 `--on-conflict`：会混淆「修补已受管漂移」与「首次吞并外来文件」，违背 ADR-0019 读者预期。
