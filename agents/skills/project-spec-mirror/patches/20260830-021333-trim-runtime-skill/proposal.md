# 精简运行时 Skill 并移除自更新冲突

- target: agents/skills/project-spec-mirror
- patch: 20260830-021333-trim-runtime-skill
- risk: medium
- status: proposed

## Intent

按 skill-creator 的渐进披露原则精简主 `SKILL.md`：

- 优化 frontmatter description，明确 WHAT、WHEN、非目标和 Git/non-Git 更新方式，消除“自动 git commit”的歧义。
- 增加 compatibility，集中声明 Python、Git 以及可选的 Node.js/archify 依赖。
- 删除运行时主文档中约 80 行 Self-evolution 流程，避免普通镜像任务自行写 experience 或调用 `skill-evolver`/`skill-upgrader`。
- 保留简短质量检查入口，指向 evals；Skill 维护和经验记录明确交给外部维护流程。

不删除 `examples/`、`evals/`、`experience/` 资产，不修改 specctl、镜像输出或前面已稳定的模式策略。

## Conflict check

- 当前 Self-evolution 同时要求 `skill-evolver`、`skill-upgrader` 和 Proposal 确认，与本仓库 `pwd-skill-manager` 的 patch 协议冲突。
- 自动在普通执行后写 experience 会扩大用户“创建/更新镜像”的授权范围。
- `evals` 仍用于任务完成前质量检查，不依赖 Self-evolution 章节。
- `experience/README.md` 改为 maintainer-only，避免目录存在被误解为运行时副作用授权。

## Rationale

项目镜像执行者只需要知道如何创建、更新和验证镜像；Skill 自身如何进化属于维护者关注点。移除无关元流程可减少上下文、职责冲突和意外写入，同时保留可发现的质量检查。

## Files

- `agents/skills/project-spec-mirror/SKILL.md` — 优化 metadata，删除 Self-evolution，保留短质量检查。
- `agents/skills/project-spec-mirror/experience/README.md` — 明确仅维护 Skill 时记录。
- `agents/skills/project-spec-mirror/tests/test_skill_contract.py` — 验证 metadata 与维护边界。

## Validation

- `git apply --check --recount` 应通过。
- `git diff --check -- agents/skills/project-spec-mirror` 应通过。
- `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests` 应通过。
- 检查主 Skill 不再包含 `skill-evolver`、`skill-upgrader` 或运行时 experience 写入指令。
