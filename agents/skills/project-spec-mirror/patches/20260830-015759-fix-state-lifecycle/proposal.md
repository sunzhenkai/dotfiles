# 修复镜像状态生命周期

- target: agents/skills/project-spec-mirror
- patch: 20260830-015759-fix-state-lifecycle
- risk: high
- status: proposed

## Intent

修复 `.mirror.json` 无法表达非 Git 项目已完成 build、允许无效 `mode/detail_level` 组合、同步指针先于验证落盘，以及 README 展示状态可能与机械状态漂移的问题。

本轮引入 `build_status: skeleton | built` 与 `built_at`；`mode=concise` 时 `detail_level` 固定为 `null`，`mode=detailed` 时才允许三档文件粒度；`set-sync --built` 在写状态前校验骨架，拒绝给非 Git 源写 commit，并机械同步 README 状态表。旧镜像缺少 `build_status` 时依据 `synced_commit` 兼容推断。

非目标：本轮不重构三档详细模式的内容语义，不放宽投影、图表、热点或单项目约束，不修正祖先目录 project 探测策略。

## Conflict check

- 现有阶段推断只依赖 `synced_commit`，与非 Git build/update 契约冲突；改为以 `build_status` 为主。
- 现有 concise 状态仍保存默认 `detail_level=important`；改为 `null`，属于状态契约变更。
- 现有 `set-sync` 可直接写状态后再由调用方运行 `validate`；改为写前校验，并要求完成 build/update 时显式传 `--built`。
- README 自然语言仍由 Agent 维护；CLI 只机械更新粒度、文件粒度、分支和同步 commit 四个状态表行，不扩展到正文生成。
- 预存量镜像保持可读；缺 `build_status` 时兼容推断，下一次 `set-sync` 会写入新字段。
- 当前测试受 `/tmp/package.json` 污染而失败；本 patch 仅隔离对应测试的祖先探测，不改变本轮非目标中的生产探测策略。

## Rationale

build 完成状态与 Git commit 是两个不同概念。拆开后，Git 和非 Git 源都能可靠进入 update，模式组合可以机械校验，失败的骨架验证不会提前推进同步状态，人读入口也不会与 `.mirror.json` 漂移。改动可由单元测试确定性验证，适用于所有使用本 Skill 的项目。

## Files

- `agents/skills/project-spec-mirror/SKILL.md` — 更新阶段推断、set-sync 命令与 build/update 完成顺序。
- `agents/skills/project-spec-mirror/references/layout.md` — 更新状态 schema 与字段含义。
- `agents/skills/project-spec-mirror/references/modes.md` — 明确合法模式组合。
- `agents/skills/project-spec-mirror/scripts/specctl.py` — 实现 build 状态、写前校验、非 Git commit 门禁和 README 状态同步。
- `agents/skills/project-spec-mirror/evals/cases.yaml` — 增加状态生命周期验收。
- `agents/skills/project-spec-mirror/tests/test_specctl.py` — 覆盖合法组合、非 Git build、写前验证和 README 一致性，并隔离已有环境依赖测试。

## Validation

- `git apply --check --recount` 应通过。
- `git diff --check -- agents/skills/project-spec-mirror` 应通过。
- `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests` 应通过。
- concise/detailed 组合、Git/non-Git build 状态、README/.mirror.json 一致性均有确定性测试。
- 检查 patch 不含隐私信息、外部仓库内容或同步镜像改动。
