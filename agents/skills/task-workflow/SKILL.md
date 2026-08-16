---
id: task-workflow
name: task-workflow
description: 跟踪一次需求交付（new/explore/design?/propose/apply/archive）；task-* 家族入口。工作区根 `.task-workflow.md` 保存跨任务特殊要求与规格。在用户要立项、跟进需求任务、把 OpenSpec change 与交付生命周期串起来时使用。复杂任务可在 explore 之后走可选的 task-design。
---

# 任务工作流

面向用户默认使用简体中文；命令、路径、代码、状态值与既成术语保持原文。

```text
task-new → task-explore? → task-design? → task-propose → task-apply → task-archive
```

`tasks/` 跟踪交付生命周期，OpenSpec change 承载可验证契约；两者并行且互不替代。`task-design` 仅用于新子系统、多方案或跨模块契约，局部且路径唯一时跳过。

## Phase 路由

每次只读本文件、下表指定 reference，以及 reference 点名的 `safety.md` 规则；不要加载其他阶段正文。

| command | reference |
|---------|-----------|
| `task-new` / `task-explore` / `task-propose` | `references/planning.md#task-<phase>` |
| `task-design` | `references/planning.md#task-design` + skill `task-design` |
| `task-apply` | `references/apply.md` |
| `task-archive` | `references/archive.md` |

跨阶段硬门禁、仓库角色与状态所有权集中在 `references/safety.md`；阶段 reference 通过规则 ID 引用，不复制算法，也不在别处复制这些表。

## taskctl

机械记账只通过与本 `SKILL.md` 同目录的 `scripts/taskctl.py`：

```bash
python3 <this-skill>/scripts/taskctl.py <command> ...
```

`<this-skill>` 由本次读取的 `SKILL.md` 绝对路径确定。PATH 上没有 `taskctl` 可执行文件，禁止运行裸 `taskctl ...`。默认从 cwd 向上寻找含 `tasks/` 的工作区；`--root` 是全局参数，必须写在子命令之前（`taskctl.py --root <workspace> <command> ...`），写在子命令之后会被拒绝。

公共命令固定为：`list`（列 active/archive）、`resolve`（唯一任务 Resolution Gate）、`set-status`、`new`、`restore`、`prepare-branches`（apply 的 checkout/worktree Gate）、`execution-context`（scope、真实 checkout、OpenSpec targets 与调度）、`advance`（原子保存进度并返回 control outcome）、`archive`（preflight 与原子 finalize）、`notes`。

完整参数以 `<command> --help` 为准。stdout 只输出 JSON，stderr 是一行摘要。退出码 2 表示需要确认/选择，不得继续写操作；1 表示硬失败。

## 公共执行契约

- 除 `task-new` 外，任何 task command 都先通过 `resolve`；本条或会话已有唯一 `TNNNN` 时必须显式传入。
- `resolve` / `new` JSON 中的 `workflow_notes` 存在时视为跨任务硬约束。
- 自然语言理解由 Agent 完成；CLI 不提取需求，也不分类未完成项。status、INDEX、工作上下文和归档移动不得手改绕过 CLI，业务正文由 Agent 写入 README/OpenSpec。
- 用户确认门出现时原样报告候选、dirty、剩余项或覆盖范围并等待选择；禁止自动 stash、reset、force checkout 或越权覆盖。
- apply 的 outcome 契约以 `references/apply.md` 的表为唯一来源。跨阶段边界：暂停类 outcome 只停本轮调度、不宣称完成，`next` 时继续独立项并禁止 testing/done，只有 `done` 才允许宣称完成并桥接 archive。

## Task 数据模型

- ID：`T` + 四位数字；新 ID 由 `tasks/INDEX.md` frontmatter `next_id` 分配。active 为 `tasks/YYYY-MM-DD/TNNNN-<slug>/`，archive 为 `tasks/archive/YYYY-MM-DD-TNNNN-<slug>/`。slug 小写 kebab-case，中文需求由 Agent 自行生成，不追问用户。
- README 小节以 `new` 生成的骨架为准；现状缺口按 `信息 / 实现 / 资产 / 配置 / 依赖确认` 记录并给出补齐方式，未知写“待确认”；涉及面区分必须（会修改）、建议（只读）、排除；工作上下文规划阶段写“尚未准备”，apply 后由 `prepare-branches` 更新。不写密钥、token 或凭证，只记录环境变量名。
- status：`draft → exploring? → designed? → proposed → in_progress/blocked → archived`。缺 status 视为 draft；README 为事实来源，INDEX 是由 CLI 同步的定位索引。

## 工作区笔记

`.task-workflow.md` 只记录跨任务仍有效的特殊要求、规格、默认涉及面和踩坑，由各 phase 从 taskctl JSON 读取；单次需求、验收和方案写 task README。用户给出稳定约定时用 `notes --set-section` 更新，禁止写入凭证。

## 输出桥接

方案未定 → `{{slash:task-explore}} TNNNN`；复杂/多方案 → `{{slash:task-design}} TNNNN`；范围已清 → `{{slash:task-propose}} TNNNN`；契约就绪 → `{{slash:task-apply}} TNNNN`；交付完成 → `{{slash:task-archive}} TNNNN`。
