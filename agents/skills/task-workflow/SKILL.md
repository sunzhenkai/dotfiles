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

`tasks/` 跟踪交付生命周期，OpenSpec change 承载可验证契约。两者分工固定：**task README 记身份、涉及面、验收与验证；OpenSpec `tasks.md` 的 checkbox 是唯一进度真相**。不要再造第三份进度记录。

`task-design` 仅用于新子系统、多方案或跨模块契约；局部且路径唯一时跳过。

## Phase 路由

每次只读本文件加下表指定的一份 reference；不要加载其他阶段正文。

| command | reference |
|---------|-----------|
| `task-new` / `task-explore` / `task-propose` | `references/planning.md` |
| `task-design` | `references/planning.md` + skill `task-design` |
| `task-apply` | `references/apply.md` |
| `task-archive` | `references/archive.md` |

`references/safety.md` 是硬门禁的唯一来源，篇幅很短，每个阶段都读。

## taskctl

机械记账只通过 `scripts/taskctl.py`。脚本入口每阶段解析一次并复用：

```bash
TASKCTL=$(command -v taskctl || echo "python3 <this-skill>/scripts/taskctl.py")
$TASKCTL <command> ...
```

`taskctl` 是安装流程写入 `~/.local/bin/` 、指向 canonical 副本的 shim；PATH 上没有它时才回退到 `<this-skill>`（本次读取的 `SKILL.md` 所在目录）。

命令固定为十条加一条维护命令：

| command | 用途 |
|---------|------|
| `new` | 分配 ID、建目录与 README 骨架 |
| `list` | 列 active（`--archived` 加归档） |
| `resolve` | 唯一任务门；不唯一时退出码 2 |
| `status` | 只读进度：README 事实 + 每个 change 的 checkbox 统计。不调 git |
| `validate-round-end` | apply 本轮结束门：精确对账当前 remaining、逐项暂缓与陈旧依赖 |
| `set-status` | apply 之外的人工改状态 |
| `prepare-branches` | 把必须仓切到任务分支，dirty/fetch 失败即 fail closed |
| `archive` | 归档校验（`--dry-run` 预检）与落盘 |
| `restore` | 把归档任务恢复为 active |
| `notes` | 读写工作区 `.task-workflow.md` |
| `sync-index` | 按 `tasks/` 实际目录重建 `INDEX.md` |

`--root` 在子命令前后均可写，两处都给且值不同即报错；默认从 cwd 向上寻找含 `tasks/` 的工作区。完整参数以 `<command> --help` 为准。

stdout 只输出 JSON，stderr 是一行摘要。退出码：**0 成功，1 硬失败（含参数错误），2 需要用户确认**。看到 2 就原样报告 CLI 给出的 `affected` / `candidates` / `prompt` 并等用户选择，确认后按 CLI 给的 `confirm_command` 重跑，不得自行扩大授权范围。

## 公共执行契约

- 除 `task-new` 外，任何 task command 都先 `resolve`；本条或会话已有唯一 `TNNNN` 时必须显式传入，不要丢掉焦点改走启发式。
- `resolve` / `new` 返回的 `workflow_notes` 存在时视为跨任务硬约束。
- 自然语言理解由 Agent 完成：CLI 不提取需求、不归纳标题、不分类未完成项。反过来，status、INDEX、工作上下文和归档移动不得手改绕过 CLI。
- 业务正文（README 各节、OpenSpec artifacts）由 Agent 写入。

## Task 数据模型

- ID 为 `T` + 四位数字，由 `new` 扫描 `tasks/` 分配，归档后不回收。active 在 `tasks/YYYY-MM-DD/TNNNN-<slug>/`，归档在 `tasks/archive/YYYY-MM-DD-TNNNN-<slug>/`。slug 小写 kebab-case，由 Agent 生成，不追问用户。
- `tasks/INDEX.md` 是 CLI 按目录扫描生成的**派生索引**，不含状态，坏了跑 `sync-index` 重建。
- README 小节以 `new` 的骨架为准：概述、涉及面、关联 OpenSpec、工作上下文、验收标准、验证记录、变更记录。explore/design 可另加小节，CLI 只读它认识的那几个。
- 涉及面角色只有 `必须`（会修改，apply 时切分支）、`建议`（只读参考）、`排除`。工作上下文由 `prepare-branches` 写入，规划阶段保持「尚未准备」。
- status：`draft → exploring? → designed? → proposed → in_progress/blocked → archived`。缺 status 视为 draft。
- 不写密钥、token 或凭证，只记录环境变量名。

## 工作区笔记

`.task-workflow.md` 只记录跨任务仍有效的特殊要求、规格、默认涉及面和踩坑；单次需求、验收和方案写 task README。用户给出稳定约定时用 `notes --set-section` 更新，禁止写入凭证。

## 输出桥接

方案未定 → `{{slash:task-explore}} TNNNN`；复杂/多方案 → `{{slash:task-design}} TNNNN`；范围已清 → `{{slash:task-propose}} TNNNN`；契约就绪 → `{{slash:task-apply}} TNNNN`；交付完成 → `{{slash:task-archive}} TNNNN`。
