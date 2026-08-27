# 移除 dotf-ui-design 共享 Skill

- target: agents/skills/dotf-ui-design
- patch: 20260827-224559-remove-dotf-ui-design
- risk: high
- status: proposed

## Intent

删除公开共享 Skill `dotf-ui-design` 及其全部 sidecar（README、references/ 下所有 refer skill、脚本与数据）。触发场景：用户明确要求移除该 skill，不再维护其作为共享能力。

非目标：
- 不移除用户本地已同步的 `~/.agents/skills/dotf-ui-design/`（由后续 sync 决定）。
- 不删除 `.agents/skills/` 下的项目级 skill（如 `pwd-skill-manager` 本身）。
- 不改动仓库中其他 skill 的核心行为，仅清理指向被删 skill 的索引/引用。

## Conflict check

- `agents/README.md` 在示例条目中列出 `dotf-ui-design`，删除后该条目失效，需同步移除。
- `agents/skills/role-based-reviewer/references/constraints.md` 在 design 角色典型下游引用 `dotf-ui-design`，删除后需改为通用描述，避免引用不存在的 skill。
- 未发现其他 skill 或脚本硬依赖 `dotf-ui-design` 的存在；同步脚本 `scripts/agents/sync.sh` 仅按目录发现 skill，删除目录后自然不会同步。

## Rationale

`dotf-ui-design` 作为路由器 skill，依赖内置的多个 refer skill 维护成本较高，且与项目当前方向（基础设施/开发环境 dotfiles）关联较弱。用户明确决定下线该能力。删除整个目录是最小且彻底的操作；同步清理两处引用可保持文档与角色约束的一致性，避免指向不存在的 skill。

## Files

- 删除 `agents/skills/dotf-ui-design/` 整目录（SKILL.md、README.md、references/ 全部内容）。
- 修改 `agents/README.md`：从示例条目中移除 `dotf-ui-design` 及其描述。
- 修改 `agents/skills/role-based-reviewer/references/constraints.md`：将 design 角色典型下游的 `dotf-ui-design` 引用替换为通用描述。

## Validation

- 应用前：`git apply --check --recount change.patch` 通过。
- 应用后：
  - `git diff --check -- agents/skills/dotf-ui-design agents/README.md agents/skills/role-based-reviewer/references/constraints.md` 无空白错误。
  - `agents/skills/dotf-ui-design/` 不再存在于工作树。
  - grep 确认仓库中无残留 `dotf-ui-design` 引用（除本 patch 目录外）。
  - 运行 `scripts/agents/doctor.py` 或相关 agents 测试确认同步发现逻辑未受损（如测试可用）。
