# 一次 shell 调用完成重锁与本地校验

- target: .agents/skills/update-external-skills
- mode: update
- patch: 20261107-084004-single-shell-run
- risk: medium
- status: proposed

## Intent

将重锁、内容变化判定和仓库校验合并为一次顺序 shell 调用，减少两轮工具往返；重锁审计全文仍落盘，但终端只显示末尾摘要，避免大段审计输出进入 agent 上下文。保持 blocked 判读、fail-open、收尾授权和后续下发流程不变。

## Conflict check

不修改 `lock_update.py`、`lock_verify.py`、Makefile 或其他 Skill 的职责。通过 `pipefail` 保留管道失败语义，通过日志文件保留完整审计证据。

## Rationale

后两步只读本地产物，必须等待重锁完成但彼此无需 agent 介入；一次调用可直接串联。`tee` 后丢弃实时副本、再读取日志末尾，既保留完整证据，也避免输出截断后重跑。

## Files

- .agents/skills/update-external-skills/SKILL.md：合并三步命令并同步日志读取说明。

## Validation

- 应用前运行 `git apply --check --recount`。
- 应用后运行 `git diff --check`，核对 frontmatter 和实际 diff。
- 用 `bash -n` 校验文档中主命令的 shell 语法；不执行会推进锁或访问网络的主流程。
