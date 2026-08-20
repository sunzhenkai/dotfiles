# 拷贝 code-review Skill

- target: agents/skills/code-review
- patch: 20260820-010341-copy-code-review
- risk: high
- status: proposed

## Intent

将用户指定的本地 `~/dotf-code-review` Skill 真相源拷贝到本仓库 `agents/skills/code-review/`，包括 `SKILL.md`、审查控制脚本及其测试，使共享 Skill 可被其他 agent 复用。保持源目录内容和行为不变。

非目标：不修改 `.agents/skills/`、任何 agent 镜像/安装目录、现有 Skill、业务代码或同步/提交/推送配置；不在本轮执行外部安装或远程操作。

## Conflict check

- `agents/skills/code-review/` 当前不存在，因此不存在覆盖现有 Skill 或历史 patch 的冲突。
- 目标 frontmatter 的 `name: code-review` 与目录名一致；职责是 diff 级代码审查，与架构评审、岗位视角评审和规格符合性评审边界清晰。
- Skill 内置远程 MR/PR 评论确认门；本次仅复制内容，不执行其远程副作用。
- 未发现绝对家目录、个人账号、凭据、内部 URL 或私有仓库内容；示例使用 `.invalid` 和占位符。

## Rationale

这是用户明确指定的、可审计的共享 Skill 导入。源目录包含完整说明、确定性机械脚本和测试，拷贝后可通过现有测试验证；保留测试有助于后续维护。由于新增触发能力并包含受确认门保护的远程评论流程，按 high 风险记录；用户已明确批准拷贝该具体目录，视为通过应用门禁。

## Files

- `agents/skills/code-review/SKILL.md`：Skill 说明、触发条件、流程与边界。
- `agents/skills/code-review/scripts/reviewctl.py`：仓库定位、审查范围解析、MR/PR 解析及报告落盘的机械命令。
- `agents/skills/code-review/tests/test_reviewctl.py`：上述脚本的确定性单元测试。

## Validation

- 应用前：`git apply --check --recount`。
- 应用后：`git diff --check -- agents/skills/code-review`、frontmatter/目录名一致性检查、隐私模式扫描，以及 `python3 -m unittest discover -s agents/skills/code-review/tests -v`。
