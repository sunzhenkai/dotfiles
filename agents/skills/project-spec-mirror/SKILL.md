---
name: project-spec-mirror
id: project-spec-mirror
description: 创建或增量维护项目的双读者 spec 镜像：briefing 给人扫读架构与业务流，agent spec 用 OpenSpec 形态写可换栈复现的功能契约。Git 源按 commit 更新。在用户要求 project spec 镜像、spec 孪生、可读规格、功能复现 spec 时使用。不用于 OpenSpec change、实现代码或只读问答；用户要求图表时委托 archify。
compatibility: Requires Python 3.10+; Git is required for commit-diff updates. Requested diagrams additionally require Node.js and an installed archify skill.
---

# Project Spec Mirror

面向用户沿用其语言（本文件用简体中文写成）。命令、路径、代码与既成术语保持原文。

机械工作只通过 `specctl`。正文由 Agent 写。验收：

1. 人只读 `briefing/`，能讲清系统是什么、主路径怎么走。
2. Agent 只读 `agent/`（不读源码与 `evidence/`）能做出功能等价实现，可换语言/框架。
3. 功能一致 = 对外契约、不变式、关键失败（L2–L3），不是同一目录树或工具链。

```bash
SPECCTL=$(command -v specctl || echo "python3 <this-skill>/scripts/specctl.py")
$SPECCTL <command> ...
```

stdout 只输出 JSON。退出码：0 成功，1 硬失败，2 需确认。看到 2 就原样报告 `prompt` / `confirm_args`，等用户同意后再用返回参数重跑。

## 非目标

- 不写入目标仓 `openspec/`。Agent 契约在 `spec_root/agent/specs/`。
- 不改目标源码、测试、构建；不自动 commit / push。
- 密钥与凭据值写 `<REDACTED>`（含 `AppKey` / `SecretKey` / token / password）。
- 不整理三方树或外来仓。默认不生成 `facets/`、模块文件表、`evidence/realization/`。
- 若 `status.layout=legacy`：阶段为 `rebuild`，见 [references/appendix.md](references/appendix.md)，不要在主路径继续写旧文件表。

## 目录

```text
<spec_root>/
├── briefing/     # 人：overview · architecture · flows · diagrams
├── agent/        # Agent：INDEX · specs/<cap>/spec.md · model · surface · data
└── evidence/source-map.md
```

能力状态只有 `draft` | `ready`。

## 禁写（briefing）

禁止源文件表、方法逐步走读（「完整逻辑」/ full logic）、语言/包管理器版本、compose/端口/启动命令。

## Agent spec 形态

```markdown
### Requirement: 库存不足时不创建订单
系统 SHALL 拒绝该订单且不扣款。

#### Scenario: 库存为 0
- **WHEN** 请求数量大于可用库存
- **THEN** 订单不创建
- **THEN** 余额不变
```

一例见 [examples/minimal-checkout.md](examples/minimal-checkout.md)。细则按需读 [references/layout.md](references/layout.md)。

## 放置

| 判定 | 镜像根 |
|------|--------|
| 目标就是 cwd 所在仓（或 `--in-project` 且仍是该仓） | `<host>/spec/` |
| 否则 | `<cwd>/spec/<project>/` |

`spec/` 不存在则 `init` 无 `--confirm` 时退出 2。已占用且无 `.mirror.json` 禁止覆盖。

## 阶段

未点名时按 `status` 的 `phase`：无镜像 → `init`；`skeleton` → `build`；`built` 且 `layout=current` → `update`；`layout=legacy` → `rebuild`（当 build）。不要把 `status` 当写作阶段。

同一时刻只维护一个 `spec_root`。

## specctl（仅此 6 个）

| command | 用途 |
|---------|------|
| `detect` | 落点、是否已有镜像、`layout` |
| `init` | 骨架；无 `--confirm` 退出 2 |
| `status` | 阶段、layout、git 新鲜度（含 commit） |
| `diff` | 相对 `synced_commit` 的文件变更 |
| `route` | 变更文件 → 能力；rename 回写 source-map |
| `finalize` | 唯一收尾：门禁 → 回写 built / commit |

全局：`--cwd` `--spec` `--source` `--project` `--branch`。

## 工作流

**init：** `detect` → `init`（先不加 `--confirm`）→ 用户同意后带 `confirm_args` 重跑 → 立刻 `build`，空骨架不算完成。

**build / rebuild：** `status`。默认 `--mode briefing`；用户要换栈复现 → `reconstructable`。写 briefing（禁写清单）+ 能力 spec + source-map。复杂业务逻辑或用户要图时再读 [references/diagrams.md](references/diagrams.md)，产物放 `briefing/diagrams/`（线性三步用列表即可）。然后 `finalize`（Git 带 `--commit`）。

**update：** `status` + `route`，只改命中的能力与跟链接的 briefing。`unmapped` 必须并入能力或写入 INDEX「未指定」。改完 `finalize`。细则见 [references/routing.md](references/routing.md)。

保留 `<!-- manual -->` 块。旧树 rebuild 的目录对照见 [references/appendix.md](references/appendix.md)。

## 完成回执

```markdown
## Spec 镜像
- 项目：<name>
- 根：`<spec_root>`
- 粒度：briefing | reconstructable
- 分支 / commit：<branch> / `<short-sha>`（非 git 则写无）
- 本轮：init | build | update | rebuild
- 变更：<改了哪些层>
```

交卷前对照 [references/checklist.md](references/checklist.md) 并看 `finalize` 是否成功。维护本 Skill 时另跑 `evals/cases.yaml` 与 `python3 -m unittest discover -s <skill-dir>/tests`。普通镜像任务不改本 Skill。
