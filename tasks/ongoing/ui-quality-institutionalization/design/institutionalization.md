# Skill institutionalization design

## 边界

**项目内可以写**：

- 具体页面名、CSS 类、token 值、截图路径、测试文件。
- 当前应用的业务语言与视觉方向。

**共享 skill 禁止写**：

- 项目名、页面名、组件类名。
- 固定像素值或本项目调色板。
- `/tmp/...` 证据路径。
- 一次性的用户抱怨或历史失败细节。

## 通用 UI contract

有 UI 交付面的复杂任务，质量画像的 design 底线必须展开为：

1. **Surface inventory**：需要覆盖的界面 / 主流程。
2. **Primitive inventory**：需要使用或建立的控件类别。
3. **Token policy**：尺寸、间距、字体、颜色、圆角、阴影等须有单一真相源。
4. **Interaction states**：default / hover / active / focus / disabled / invalid / loading / empty / error 中与范围相关者。
5. **Viewport & theme matrix**：至少覆盖任务声明的桌面 / 窄屏 / 明暗主题组合。
6. **Evidence contract**：截图、DOM 尺寸断言、对比度或可访问性证据。
7. **Migration policy**：增量迁移，不允许业务代码绕过 primitive 写 inline magic layout。

## 建议落点

### task-wizard

修改 `references/quality-profile.md`：

- 在 design 底线或专门小节中加入“UI 交付面必须提供 UI contract”。
- 说明无 UI 任务写“不适用 + 原因”，不得编造。
- 不定义具体 token 或组件名。

### delivery-loop

修改 normal 派发与 evidence manifest：

- normal 实现者必须收到 UI contract 或保留语义的子范围裁剪。
- benchmark 仍不泄露 UI contract。
- evidence manifest 增加 UI surface / state / viewport 矩阵字段。
- 不复制 taskflow rubric 数字口径。

### role-based-reviewer

design 角色已有 token、状态、一致性与可访问性检查。只需补通用微观检查项，不写项目专有细节：

- 同区域控件高度 / 密度一致。
- 同行 input / select / button 对齐。
- hover 不引起布局跳动，不默认使用突兀 underline。
- 业务代码不得绕过 primitive 写 inline magic layout。
- UI 证据矩阵是否覆盖声明范围。

### taskflow

不复制 UI contract 字段定义；继续作为编排与 rubric 真相源。若需要，仅在质量画像传递说明中引用“上游 UI contract 原文快照”。

## Static gate mechanism

- Shared skill behavior is represented in each skill's deterministic `evals/cases.yaml`; these cases describe generic UI contract behavior, not project names or pixels.
- The task-level regression script may check local implementation anchors, but it is not the shared truth source.
- A generic validator may be added to `delivery-loop/scripts/` only if YAML expectations become insufficient; it must accept a contract path and optional forbidden-term list, never hardcode a project name or pixel value.
- Open-source privacy validation uses a caller-supplied forbidden-term list plus existing secret scan; no project-specific word list is baked into the skill.

## Planned skill changes are first-class changes

The skill updates are planned deliverables, not failure-triage afterthoughts. They run as a separate taskflow child change / skill-upgrader patch stream:

- project UI migration child change;
- shared skill institutionalization child change;
- final cross-review and full-chain validation.

This keeps implementation failures and planned skill evolution in separate accounts while both remain inside the same delivery-loop objective.

## Patch / validation

1. task-wizard、delivery-loop、role-based-reviewer 均走 `skill-upgrader` patch。
2. 每个 patch 先 `git apply --check`，再应用并写 result。
3. 新增 eval case：
   - UI 任务缺 contract 阻止开工。
   - normal 派发携带 UI contract。
   - benchmark 不泄露 UI contract。
   - design review 检查微观一致性与证据矩阵。
4. 同步 OpenSpec / ADR：
   - task-wizard-goal：UI contract 进入质量画像门。
   - taskflow-orchestration / delivery-loop 若无独立 spec，则在现有 spec 或 ADR 中说明通用契约。
5. 静态门增加：
   - UI contract 存在。
   - normal / benchmark 输入差异。
   - design reviewer 微观检查存在。
   - 无项目专有词。
