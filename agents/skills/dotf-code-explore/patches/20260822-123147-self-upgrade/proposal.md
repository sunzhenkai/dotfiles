# 将代码探索 Skill 升级为可自进化结构

- target: agents/skills/dotf-code-explore
- mode: self-upgrade
- patch: 20260822-123147-self-upgrade
- risk: medium
- status: proposed

## Intent

为已有 dotf-code-explore 增加标准的 examples、evals、experience 自进化目录，并在 SKILL.md 末尾注入经验积累、Eval 校验和演进门禁。保留现有 ask、explore、archive、ingest、project 工作流及只读边界；不编造成功案例、失败案例或历史经验，不改动 agents/openai.yaml，不修改已有 patches 审计记录。

## Conflict check

目标 Skill 当前没有 examples、evals、experience 目录，也没有 Self-evolution 段落，因此不是重复升级。现有 SKILL.md 已要求只读探索、显式写入门槛、证据与审计；注入内容只补充经验和 Eval 的生命周期约束，不放宽这些安全边界。现有目标没有 tests/，因此 regression cases 留空，不虚构历史回归。

## Rationale

self-upgrade 模式的标准目录、README、Eval schema 和注入段落来自 skill-upgrader 的模板，并与目标 Skill 的阶段、只读约束、交付格式和证据规则相匹配。Eval cases 仅从现有正文抽取可观察的触发、主流程、禁止行为和边界，不添加原文没有的能力；空 experience 子目录明确表示当前没有真实经验条目。

## Files

- agents/skills/dotf-code-explore/SKILL.md — 末尾追加 Self-evolution 规则。
- agents/skills/dotf-code-explore/examples/README.md — 添加案例目录约定，不伪造案例。
- agents/skills/dotf-code-explore/evals/README.md — 添加 Eval 使用说明。
- agents/skills/dotf-code-explore/evals/cases.yaml — 添加从现有正文抽取的确定性与少量语义 Eval cases。
- agents/skills/dotf-code-explore/experience/README.md — 添加真实经验记录约定。
- agents/skills/dotf-code-explore/experience/{failures,successes,patterns}/.gitkeep — 保留空经验分类目录。

## Validation

- 运行 git apply --check --recount 校验 patch。
- 应用后运行 git diff --check，并验证 SKILL.md frontmatter、目录结构、Eval YAML、注入段落和原有正文保留。
- 确认 examples 与 experience 没有伪造案例，目标外文件和历史 patches 未被修改。
