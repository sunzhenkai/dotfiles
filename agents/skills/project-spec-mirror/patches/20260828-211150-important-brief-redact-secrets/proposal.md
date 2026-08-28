# important 写简述且禁止抄密钥字面量

- target: agents/skills/project-spec-mirror
- patch: 20260828-211150-important-brief-redact-secrets
- risk: high
- status: proposed

## Intent

改变详尽默认档 `important` 的写作行为，并收紧镜像脱敏：

1. 不再把非重要文件整份忽略。范围内每个源文件至少出现在模块文件表：重要文件整理（职责 + 核心符号），其余写一句话简述；简单文件仍可合并登记。
2. `important` 模块页必须达到「标题一句职责、根路径、文件表、核心符号」的最低密度，而不是只留几行空表。
3. 源码里的 `AppKey` / `SecretKey` 等凭据字面量不得抄进文件表、核心符号或配置说明；只写字段名与注入方式，值一律 `<REDACTED>`。

非目标：不改 `complete` / `lightweight` 的档位含义；不改路由标题（仍用「根」「文件」）；不铺 `notes/`；不改 inventory 跳过密钥文件名的机械规则。

## Conflict check

与上一档「important 可忽略无业务含义文件」冲突，这正是要改的错误规则。与「不把每个源文件做成规格页」不冲突：简述仍是表行，不是一文件一页。与已有「密钥写 `<REDACTED>`」不冲突，只是把源码常量/字段赋值也算原文。示例使用虚构客户端，不写入真实产品或仓库路径。

## Rationale

`important` 若整份省略文件，模块页信息过少，无法回答「这个包有哪些文件、关键符号做什么」。把忽略改成简述后，完整度接近用户给出的模块页密度，同时仍比 `complete` 浅。源码常量里的 AppKey/SecretKey 被当成「职责」抄进镜像属于严重泄密，必须写成可执行的禁令，而不是只跳过 `.env` 文件名。

## Files

- `agents/skills/project-spec-mirror/SKILL.md` — 公共契约与 build 步骤：简述替代忽略；点名 AppKey/SecretKey 等字面量。
- `agents/skills/project-spec-mirror/references/modes.md` — 重写 important 档位、最低密度示例与脱敏约束。
- `agents/skills/project-spec-mirror/references/layout.md` — 模块页补「核心符号」；文件表不得漏行。
- `agents/skills/project-spec-mirror/references/projections.md` — 恢复自检脱敏覆盖密钥字面量。
- `agents/skills/project-spec-mirror/evals/cases.yaml` — 同步 important 与密钥验收。
- `agents/skills/project-spec-mirror/tests/test_skill_contract.py` — 锁定简述与脱敏措辞。
- `agents/skills/project-spec-mirror/experience/failures/20260828-secret-literals-in-spec.md` — 记录本次纠正（脱敏，无真实产品信息）。

## Validation

- `git apply --check --recount` 应通过。
- `git diff --check -- agents/skills/project-spec-mirror` 应通过。
- `python3 -m unittest discover -s agents/skills/project-spec-mirror/tests` 应通过。
- 生产正文不含真实产品名、绝对家目录或密钥原文。
