# 拓宽「开发/测试启动约定」的判定信号，覆盖开发环境/开发栈/dev 命名

- target: agents/skills/service-manager
- mode: update
- patch: 20260921-222519-dev-bind-scope-signals
- risk: low
- status: proposed

## Intent

「绑定 0.0.0.0」与「优先热更新」约定此前仅在 `source` 类型或 notes 标明 dev/test 时触发。用户指出：被识别为**开发环境 / 开发栈**、或服务名 / command 含 `dev` 语义的本地原生服务也应同样适用。本 patch 在适用条款中显式列出这些判定信号（任一即可），不改变豁免项与例外处理。

非目标：不改热更新优先级、不改 0.0.0.0 补绑步骤、不触及 compose 服务豁免。

## Conflict check

- 与「不强制改写」豁免条款（人工标注、用户指定 command、生产向 start/serve、compose 依赖类服务）无冲突，原文保留。
- 与「优先热更新方式」中 `dev`/`serve:dev` 命名线索一致，此处复用同一信号而非引入新概念。
- 与其他 Skill 职责无交叉。

## Rationale

属 writing-for-agents 的 pointer 分支补全：规则正文存在，但触发分支未枚举「开发环境 / 开发栈 / dev 命名」这条路径，agent 在这些场景下不一定会到达规则。改动通用（不绑定本仓库）、可执行（判定信号可观察）、可验证（start 后可从 notes / 监听地址确认）。

## Files

- `agents/skills/service-manager/SKILL.md`：「开发/测试启动约定」适用条款列出判定信号。

## Validation

- 应用前：`git apply --check --recount` 于仓库根通过。
- 应用后：`git diff --check`；确认豁免条款原文未变；grep 确认 0.0.0.0 规则正文未动。
