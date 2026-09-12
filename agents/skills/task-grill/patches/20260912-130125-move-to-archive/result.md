# task-grill 移入归档目录 — 结果

status: applied

## 实际改动

与 `change.patch` 一致：

- 新建 `agents/skills-archive/README.md`（归档规则 + task-grill 恢复清单 + 现存归档表）；
- 新建 `agents/skills-archive/task-grill/SKILL.md`、`agents/skills-archive/task-grill/agents/openai.yaml`，内容与删除前逐字节一致（与 `git show HEAD:...` diff 为空）；
- `agents/README.md`「不要手改」段后新增一句归档目录说明。

偏差：patch 路径含 `agents/skills-archive/...`，超出 pwd-skill-manager 的 `agents/skills/<skill-name>/` 前缀约定——本轮为跨目录移动，无法套用前缀；审计历史仍留在 `agents/skills/task-grill/patches/`。

## 验证

- `git apply --check --recount` 通过；应用后 `git diff --check` 无空白错误；
- 归档副本与原生产内容逐字节一致；
- `pytest -k "agents or skill or catalog or coverage"`：191 passed，2 failed——均为 `wayfinder`/`code-review` 编目注释（用户在途改动）与本机 overlay `00-local.yaml` 的既有冲突，与本轮无关；
- `agents/skills/` 下 task-grill 仅剩 `patches/`，无 SKILL.md，不触发 coverage 校验。

## 恢复方式

见 `agents/skills-archive/README.md`：移回 `agents/skills/task-grill/` → `agents/skills.yaml` 加回编目 → 按 `patches/20260912-125452-archive-skill/change.patch` 的删除 hunk 恢复 6 处引用 → `dotf agents -c`。

## 后续

- 未执行 commit / push。
