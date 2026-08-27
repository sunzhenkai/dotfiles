# 创建 project-spec-mirror

- target: agents/skills/project-spec-mirror
- patch: 20260827-111251-create-skill
- risk: high
- status: proposed

## Intent

新增公开共享 Skill `project-spec-mirror`：为单个目标 project 维护给人读的 spec 孪生目录。

触发：用户要求创建/更新 project spec 镜像、spec 孪生、可读规格目录，或点名本 Skill。

非目标：OpenSpec change、改源码、只读代码问答、自动 commit。

行为要点：

- 放置：cwd 是 project 根 → `spec/`；否则 → `spec/<project>/`。子目录要用仓库根时显式 `--in-project`。
- `spec/` 不存在则确认后创建；已占用且无 `.mirror.json` 则拒绝覆盖。
- git 源默认跟踪默认分支，记录同步 commit；支持 `--branch`；update 读 `synced_commit..target` diff。
- 简约 / 详尽两档；金字塔目录；自动识别并维护概念、实体、业务处理线。
- `specctl`（python3）只做机械工作；正文由 Agent 写。

## Conflict check

- 与 `task-workflow` / OpenSpec：后者是实现契约与交付进度；本 Skill 固定目录名 `spec/`，明确不写入 `openspec/`。
- 与 `dotf-code-explore`：后者是只读问答与可选知识归档；本 Skill 是持续维护的可读孪生。
- 仓库内无同名 Skill。none 以外的职责重叠通过非目标声明隔开。

## Rationale

跨项目可复用：放置规则、git 指针、忽略清单、符号提取都不绑特定仓库。`specctl` 有确认门与 unittest，可验证。详尽模式对大库用范围与 80 文件询问约束，避免不可维护的全量详页。

## Files

- `agents/skills/project-spec-mirror/SKILL.md` — 阶段、放置、specctl 契约
- `agents/skills/project-spec-mirror/references/layout.md` — 金字塔与模板
- `agents/skills/project-spec-mirror/references/modes.md` — 简约/详尽
- `agents/skills/project-spec-mirror/references/knowledge.md` — 概念/实体/处理线
- `agents/skills/project-spec-mirror/scripts/specctl.py` — 机械 CLI
- `agents/skills/project-spec-mirror/tests/test_specctl.py` — 行为测试
- `agents/skills/project-spec-mirror/tests/test_skill_contract.py` — 文档与命令表一致性

## Validation

- 应用前：`git apply --check --recount` 本 patch
- 应用后：`git diff --check -- agents/skills/project-spec-mirror`；`python3 -m unittest discover -s agents/skills/project-spec-mirror/tests`
- frontmatter `name`/`id` 与目录名一致；引用路径存在；无私有信息
