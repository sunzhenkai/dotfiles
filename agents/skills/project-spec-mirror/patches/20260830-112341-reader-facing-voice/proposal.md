# 给人读的正文用项目口吻

- target: agents/skills/project-spec-mirror
- patch: 20260830-112341-reader-facing-voice
- risk: medium
- status: proposed

## Intent

改变模型写进镜像正文的口吻：README、overview 和其他给人读的页用项目自己的语言说话。标题写项目名或该页主题，开篇写这个项目/这页回答什么。

不再把「Spec 镜像」「孪生规格」「不是 OpenSpec」「验收：只凭本镜像能重建」当成标题或第一句。这些是 Skill 内部验收，不是读者打开目录后该看到的宣言。

不改 Skill 触发条件，不改 Agent 对用户的完成回执（对话里仍可用「Spec 镜像」）。不改 changelog / `.mirror.json` 这类操作记录的用语。

## Conflict check

与现有金字塔、恢复投影、切面职责无冲突。`set-sync` / `validate` 只核对 README 状态表的「粒度 / 文件粒度 / 分支 / 同步 commit」，不依赖旧标题。

Skill 正文、description 里仍可出现「给人读的规格孪生」，那是给 Agent 的说明，不是镜像页。

## Rationale

读者打开 `spec/README.md` 是来理解这个项目的。制作过程用语会把他们拉出项目语境。规则可执行、可验证：标题与开篇能对照项目名和一句话职责；禁止清单可 grep。跨项目成立，不依赖本机特例。

## Files

- `agents/skills/project-spec-mirror/references/layout.md` — 写入口模板与读者口吻规则
- `agents/skills/project-spec-mirror/scripts/specctl.py` — init 骨架 README 与模板对齐
- `agents/skills/project-spec-mirror/tests/test_skill_contract.py` — 锁定禁止用语与规则存在
- `agents/skills/project-spec-mirror/evals/cases.yaml` — build 输出不得用制作过程用语开篇

## Validation

- 应用前：`git apply --check --recount` 本 patch
- 应用后：`git diff --check -- agents/skills/project-spec-mirror`；`python3 -m unittest discover -s agents/skills/project-spec-mirror/tests`
