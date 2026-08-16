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

| command | reference | 说明 |
|---------|-----------|------|
| `task-new` | `references/planning.md#task-new` | 创建编号 task，归纳需求与计划涉及面 |
| `task-explore` | `references/planning.md#task-explore` | 探索问题与方案，不写业务代码 |
| `task-design` | `references/planning.md#task-design` + skill `task-design` | 可选决策级设计 |
| `task-propose` | `references/planning.md#task-propose` | 生成并关联 OpenSpec changes |
| `task-apply` | `references/apply.md` | 准备真实 checkout 并持续实施 |
| `task-archive` | `references/archive.md` | Initial/External/Final 可恢复归档 |

跨阶段硬门禁集中在 `references/safety.md`；阶段 reference 通过规则 ID 引用，不复制算法。

## taskctl

机械记账只通过与本 `SKILL.md` 同目录的 `scripts/taskctl.py`：

```bash
python3 <this-skill>/scripts/taskctl.py <command> ...
```

`<this-skill>` 必须由本次读取的 `SKILL.md` 绝对路径确定。PATH 上没有 `taskctl` 可执行文件，禁止直接运行裸 `taskctl ...`。默认从 cwd 向上寻找含 `tasks/` 的工作区；可显式传 `--root`。

公共命令固定为：

| command | 职责 |
|---------|------|
| `list` | 列出 active/archive task |
| `resolve` | 唯一任务 Resolution Gate |
| `set-status` | 原子同步 README 与 INDEX status |
| `new` | 分配 TNNNN、创建骨架、更新 INDEX |
| `restore` | 将 archived task 原子恢复为 active |
| `prepare-branches` | apply 的 delivery checkout/worktree Gate |
| `execution-context` | 返回 scope、真实 checkout、OpenSpec targets 与调度 |
| `advance` | 原子保存 apply 进度并返回六种 control outcome |
| `archive` | initial/final preflight、external action 状态与原子 finalize |
| `notes` | 读写工作区 `.task-workflow.md` |

完整参数以 `python3 .../taskctl.py <command> --help` 为准。stdout 只输出 JSON；stderr 是一行人读摘要。退出码 2 表示需要确认/选择，不得继续写操作；退出码 1 表示硬失败。

## 公共执行契约

- 除 `task-new` 外，任何 task command 都先通过 `resolve`；本条或会话已有唯一 `TNNNN` 时必须显式传入。
- `resolve` / `new` JSON 中的 `workflow_notes` 存在时视为跨任务硬约束；无需为缺失 notes 创建空骨架。
- 自然语言理解由 Agent 完成。CLI 不提取需求，不分类未完成项是验证还是实现。
- status、INDEX、工作上下文和归档移动不得手改绕过 CLI；业务正文由 Agent 写入 README/OpenSpec。
- 用户确认门出现时原样报告候选、dirty、剩余项或覆盖范围，等待明确选择；禁止自动 stash、reset、force checkout 或越权覆盖。
- apply 的 `blocked` / `deferred_only` / `validation_required` 只停本轮调度，不宣称完成；只有 `done` 才允许宣称完成并桥接 archive。

## Task 数据模型

### 编号与目录

- ID：`T` + 四位数字，例如 `T0001`；新 ID 由 `tasks/INDEX.md` frontmatter `next_id` 分配。
- active：`tasks/YYYY-MM-DD/TNNNN-<slug>/`
- archive：`tasks/archive/YYYY-MM-DD-TNNNN-<slug>/`
- slug：小写 kebab-case。中文需求由 Agent 自行生成英文 slug，不追问用户。

### README

README 至少包含：id/status/slug/创建时间、概述、背景、目标、现状缺口、需求说明、验收标准、涉及面、工作上下文、关联 OpenSpec、设计文档、变更记录。

- 现状缺口按 `信息 / 实现 / 资产 / 配置 / 依赖确认` 记录并给出补齐方式；未知写“待确认”。
- 涉及面区分必须（会修改）、建议（只读）、排除；只有必须仓属于 delivery。
- 工作上下文记录实际 canonical repo、checkout/worktree、branch/base。规划阶段写“尚未准备”；apply 后由 `prepare-branches` 更新。
- 不写密钥、token 或数据库凭证；只记录环境变量名。

### status

`draft → exploring? → designed? → proposed → in_progress/blocked → archived`。缺 status 视为 draft；README 为事实来源，INDEX 是由 CLI 同步的定位索引。

## 仓库角色与状态所有权

| role | 来源 | 约束 |
|------|------|------|
| delivery | 必须仓、工作上下文 checkout | apply 准备；archive 必须 valid、同源、clean |
| planning | OpenSpec planning root | 校验 change；dirty 只诊断 |
| task_store | 保存 tasks/INDEX 的工作区仓 | 依靠锁和回滚；dirty 只诊断 |
| reference | 建议/排除仓 | 不切分支、不检查状态 |

同仓多角色时 delivery 优先。工作区 `.` 仅在工作区自身确为必须修改仓时才是 delivery。

状态事实：README 保存 task/scope/work context；INDEX 保存 ID 与定位；OpenSpec `tasks.md` 保存完成度；`.task-apply-state.json` 保存 deferred；`progress.md` 保存 `advance` 生成的阶段与验证证据；Git 保存 checkout/branch/dirty。不得增加镜像真相源。

## 工作区笔记

`.task-workflow.md` 只记录跨任务仍有效的特殊要求、规格、默认涉及面和踩坑。每个 phase 从 taskctl JSON 读取；单次需求、验收和方案写 task README。用户给出稳定约定时用 `notes --set-section` 及时更新，禁止写入凭证。

## 输出桥接

- 方案未定 → `{{slash:task-explore}} TNNNN`
- 复杂/多方案 → `{{slash:task-design}} TNNNN`
- 范围已清 → `{{slash:task-propose}} TNNNN`
- 契约就绪 → `{{slash:task-apply}} TNNNN`
- 交付完成 → `{{slash:task-archive}} TNNNN`
