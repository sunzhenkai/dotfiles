# 添加代码探索 Skill

- target: agents/skills/dotf-code-explore
- patch: 20260822-122535-add-code-explore
- risk: medium
- status: proposed

## Intent

将用户指定的本地 `dotf-code-explore` Skill 复制为仓库共享 Skill `agents/skills/dotf-code-explore/`，使其可用于回答代码问题、追踪调用链、评估变更影响以及整理项目知识。保留其现有的只读探索边界和 OpenAI Skill 展示元数据；不修改源文件内容，不同步到其他 agent 镜像目录。

## Conflict check

目标目录当前不存在，没有现有 `SKILL.md`、frontmatter、测试或脚本冲突。该 Skill 的目录名与 frontmatter 的 `name: dotf-code-explore` 一致；其职责是代码理解工作流，与现有共享 Skill 不构成直接职责冲突。源目录仅包含 `SKILL.md` 和 `agents/openai.yaml`，未发现绝对路径、凭据、个人联系方式或私有 URL。

## Rationale

这是用户明确指定的完整 Skill 复制，内容面向跨仓库复用，使用 `REPO_ROOT`、`KNOWLEDGE_ROOT`、`PROJECT_ROOT` 等通用占位符，且包含可验证的只读、安全和审计规则。复制两个现有文件即可完整保留 Skill 的行为与展示配置，不需要额外重写。

## Files

- `agents/skills/dotf-code-explore/SKILL.md` — 新增共享 Skill 正文。
- `agents/skills/dotf-code-explore/agents/openai.yaml` — 新增 Skill 展示名称、简介和默认提示。

## Validation

- 从仓库根执行 `git apply --check --recount` 校验 patch。
- 应用后执行 `git diff --check`。
- 检查 frontmatter、目录名、引用路径和隐私模式；确认只新增声明的两个生产文件及本轮审计记录。
