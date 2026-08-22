# 完成后输出三项总结

- target: agents/skills/service-manager
- patch: 20260822-101102-completion-summary
- risk: medium
- status: proposed

## Intent

- **行为**：任一 phase 结束后，在主输出之后强制给出简短总结，覆盖改动范围、影响面、服务访问方式。
- **触发**：`list` / `start` / `stop` / `restart` / `status` / `logs` 执行完毕（成功或可报告的失败）。
- **非目标**：不改变启动/停止/杀进程逻辑；不改变缓存或 `.service-manager.md` 的读写规则；不引入新 phase。

## Conflict check

- 与现有 phase、安全边界、两层信息协议无冲突；仅扩展输出契约。
- 不与 `skill-evolver` 或其他 Skill 职责重叠。
- 新增 eval `completion-summary`，与既有 case 不重复。

## Rationale

服务启停后用户最需要知道「动了什么、波及什么、怎么访问」。把三项总结写进共享 Skill，跨项目可复用，且可用确定性 eval 校验。

## Files

- `agents/skills/service-manager/SKILL.md`：frontmatter description 补充；在「安全与边界」前新增「完成后总结」节。
- `agents/skills/service-manager/evals/cases.yaml`：新增 `completion-summary` case。

## Validation

- `git apply --check --recount` 对 `change.patch`
- 应用后 `git diff --check -- agents/skills/service-manager`
- 核对 `name` 与目录一致、无隐私信息、未改 `patches/` 历史
