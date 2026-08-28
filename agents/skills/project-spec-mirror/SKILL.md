---
id: project-spec-mirror
name: project-spec-mirror
description: >-
  为项目维护给人读的 spec 孪生目录：金字塔、恢复投影（上下文/数据/表面/运行时/构建）、
  工程切面（来源/契约/切片/验证/流量）、简约/详尽模式及详尽下的文件整理粒度，并用 git commit 做增量更新。
  图表委托 archify。验收是只凭镜像能重建可运行系统。在用户要求创建或更新 project spec
  镜像、spec 孪生、可读规格目录、工程切面，或点名 project-spec-mirror 时使用。
  不要用于 OpenSpec change、实现代码或只读问答。
---

# Project Spec Mirror

面向用户默认使用简体中文。命令、路径、代码、标识符与既成术语保持原文。

为**一个目标 project** 维护给人读的规格孪生，不是实现契约、不是源码副本。机械工作只通过 `specctl`；金字塔、恢复投影、切面正文由 Agent 撰写。验收档 C：只凭镜像能重建可运行系统。需要结构图、流程、时序、数据流或状态机时，委托 skill `archify`（[tt-a1i/archify](https://github.com/tt-a1i/archify)），产物放 `diagrams/`。

```bash
SPECCTL=$(command -v specctl || echo "python3 <this-skill>/scripts/specctl.py")
$SPECCTL <command> ...
```

stdout 只输出 JSON，stderr 是一行摘要。退出码：**0** 成功，**1** 硬失败，**2** 需要用户确认。看到 2 就原样报告 `prompt` / `confirm_args`，等用户明确同意后再带上 CLI 给出的参数重跑，不得自行扩大范围。

## 非目标

- 不是 OpenSpec / `openspec/` / 实现 change；不要把镜像写进那些目录。
- 不修改目标 project 的源码、测试、构建或依赖。
- 不代替 README 成为项目对外文档；镜像服务「给人把项目读清楚」。
- 不自动 commit / push；不把密钥、`.env`、凭据写进镜像。
- 不把每个源文件做成规格页；文件只做清单行、路由键和证据路径。
- 不整理三方依赖源码，也不整理本工程所依赖的其他仓库代码。镜像只覆盖当前 `--source` 工程自己的代码。
  - 跳过包管理器安装树：`vendor/`（Go / PHP Composer 等）、`node_modules/`、虚拟环境及同类目录（与 `inventory` 忽略规则一致）。
  - 跳过 git submodule、树内嵌套仓库、以及 `replace` / Composer path / 同级克隆等外来仓。邻接只在 `context/` 记边界与协议；包名与版本约束只在 `build/` 点到为止。
  - 不要为三方或外来仓建模块、文件表行、`notes/`、概念或切片。需要给那个仓做镜像时，另开一次会话并显式 `--source`。

## 放置规则

落点由 **cwd 是不是当前仓** 和 **目标 source/`--project` 是不是这个仓** 一起决定（可用 `--cwd` 覆盖）：

| 判定 | 镜像根 |
|------|--------|
| 目标就是 cwd 所在仓（cwd 为该仓根，或 `--in-project` 且目标仍是该仓） | `<host>/spec/` |
| 目标不是当前仓：`--source` 指向另一仓，或 `--project` 与当前仓名不同 | `<cwd>/spec/<project>/` |
| cwd 不是 project 根，且未加 `--in-project` | `<cwd>/spec/<project>/` |

- **当前仓 / host**：cwd 为 project 根时即 cwd；`--in-project` 时为向上找到的 project 根。身份优先用 git 根比较，否则用 project 根路径。
- project 根：目录含 `.git`，或含 `go.mod` / `package.json` / `pyproject.toml` / `Cargo.toml` 等语言清单（完整列表见 `specctl detect`）。
- `--in-project` 只在目标仍是 host 时把镜像放到仓库根 `spec/`。目标是外来仓时忽略该旗标，走 `spec/<project>/`，避免占掉当前仓自己的镜像位。
- `<project>` 来自 `--project`；未给时用 `--source` 的目录名。外来仓或非工程目录首次 init 必须能确定 project 名；外来仓还必须有 `--source`。
- `spec/`（或 `spec/<project>/`）不存在时：**先确认再创建**。`init` 无 `--confirm` 时退出码 2。
- 目录已存在但没有 `.mirror.json`：视为占用，退出码 2，禁止覆盖。
- 已有镜像：`--project` 时优先 `spec/<project>/`，不要被当前仓根上遗留的 `spec/.mirror.json` 抢走。

状态文件是 `.mirror.json`（机械真相）。源路径尽量写成相对镜像根的相对路径。

## 阶段

未点名阶段时按现状推断，并用一行说明：无镜像 → `init`；已 init 未同步 → `build`；已有 `synced_commit` → `update`；只改某一词条 → `maintain`。

| 阶段 | 做什么 | 先读 |
|------|--------|------|
| `init` | 探测、确认、写骨架 | 本文件 |
| `build` | 按粒度生成金字塔 + 恢复投影 + 切面 | [layout.md](references/layout.md)、[modes.md](references/modes.md)、[knowledge.md](references/knowledge.md)、[projections.md](references/projections.md)、[facets.md](references/facets.md)、[diagrams.md](references/diagrams.md)、[routing.md](references/routing.md) |
| `update` | 用 git diff 把变更文件路由到已有页 | 同上，只加载受影响层 |
| `maintain` | 改概念/实体/流/模块/切面/图/恢复投影中的指定条目 | 对应 reference |
| `status` | 只读同步状态 | 本文件 |

一次会话只服务**一个** target project。

## specctl

| command | 用途 |
|---------|------|
| `detect` | 判定 project 根、放置方式、是否已有镜像 |
| `init` | 建目录骨架与 `.mirror.json`；缺确认时退出 2 |
| `status` | 镜像状态 + git 新鲜度 |
| `inventory` | 源文件清单（已忽略构建产物、密钥、三方安装树与外来仓） |
| `symbols` | 从代码文件提取函数/类型/变量，供详尽模式填写模块表与热点页 |
| `git-info` | 是否 git、默认分支、指定分支的 commit |
| `diff` | 相对 `synced_commit`（或 `--from`）的文件级变更（同样忽略三方/外来仓） |
| `route` | 把 `diff` 的文件映射到模块 README（文件表 / 根前缀 / unmapped / rename） |
| `set-sync` | 正文写完后回写 commit / branch / mode / scope / hotspots / 时间 |
| `validate` | 金字塔、恢复投影、切面骨架与 `.mirror.json` 完整性 |

完整参数以 `$SPECCTL <command> --help` 为准。常用全局：`--cwd`、`--spec`、`--source`、`--project`、`--branch`。

## 公共执行契约

1. 任何写入阶段都先 `detect`（或 `status`）。不要手建目录绕过 `init`。
2. 自然语言、分层叙述、交叉链接由 Agent 完成。CLI 不写概述、不抽概念、不编流程。
3. 目标是 git 仓库时：默认跟踪**默认分支**（`origin/HEAD` → `main`/`master` 回退）。用户指定 `--branch` 则记录该分支的 commit，而不是随意的工作区 HEAD。
4. 非 git 源：仍可 init/build/maintain；`status` 标明无 commit；`update` 不能做 commit diff，改为对 `inventory` 做全量对照并说明限制。
5. 更新时保留 `<!-- manual -->` … `<!-- /manual -->` 块，不得覆盖。
6. 发现密钥形态内容：镜像里写 `<REDACTED>`，并在输出中说明省略，不把原文抄进 spec。

## 工作流

### init

1. `$SPECCTL detect`
2. 没有镜像 → `$SPECCTL init ...`（不要先加 `--confirm`）
3. 退出码 2：向用户展示 `prompt` 与将创建的 `spec_root` / `source` / `placement`，得到明确同意后用返回的 `confirm_args` 重跑
4. 成功后只存在骨架，接着进入 `build`，不要把空目录当成已完成

### build

1. `$SPECCTL status` 与 `$SPECCTL inventory`；详尽模式先确认 `detail_level`（默认 `important`），再仅对所选范围内且将写入模块表或热点页的文件跑 `symbols`
2. 读 [layout.md](references/layout.md) 按金字塔写正文；粒度见 [modes.md](references/modes.md)
3. 识别并维护恢复投影（上下文、数据、表面、运行时、构建），见 [projections.md](references/projections.md)。结束前做恢复完备自检
4. 识别并维护概念、实体、业务处理线，见 [knowledge.md](references/knowledge.md)
5. 识别并维护工程切面（来源、契约、切片、验证、流量），见 [facets.md](references/facets.md)。切片不必等全部契约写完；先 identified / characterized 再补 specified。VERIFY 在单实现时也要写如何用测试/性质证明行为；TRAFFIC 无灰度也要写发布与回滚，没有则写「无」
6. 模块地图、切片主路径、状态机等需要图时，按 [diagrams.md](references/diagrams.md) 调用 `archify`，HTML 写入 `diagrams/`
7. 每个模块 README 必须有「根」表与「文件」表（[routing.md](references/routing.md)）。详尽模式必须采用一种 `detail_level`：`complete` 完整整理；`important` 只整理重要文件并忽略或合并简单文件；`lightweight` 沿用当前轻量规则。重要文件模式只能忽略无业务含义文件。用户要「每个文件一页」时说明新模型，改为 `complete` 或热点；要热点详注且未给路径：先问（建议切片入口或一次 ≤15 个文件），未同意不批量建 `notes/`。遗留 `modules/*/files/` 停更、不删，并在模块 README 注明可能过期
8. 写完 `$SPECCTL set-sync --commit <id> --branch <name> --mode <concise|detailed> --detail-level <complete|important|lightweight>`（详尽默认 `important`，有热点则加 `--hotspot`），再 `$SPECCTL validate`
9. 向用户给出镜像根路径、怎么读（先 overview，再恢复投影，再切面/金字塔）、同步 commit

### update

1. `$SPECCTL status` 与 `$SPECCTL route`（内部用与 `diff` 相同的 `synced_commit..目标分支 commit`；可加 `--from` / `--to`）。按返回的 `modules` / `pages` / `renames` / `unmapped` 改页，不要手算、不要绕过 `route`
2. 只改映射到的模块 README 与跟链接的概念、实体、处理线、恢复投影、切面与相关图；rename（`status=R`）改文件表路径，不当删+增。上层概述若结论变了才改
3. 若缺 `context/` `data/` `surface/` `runtime/` `build/`、`facets/` 或 `diagrams/` 骨架，先补 INDEX（及 `surface/config.md`、切面短页），再改正文；不删已有金字塔
4. 工作区脏或当前分支与记录分支不一致：在输出中说明，仍以 `--branch`（默认默认分支）的 commit 为准，不要把未提交改动默认为已同步
5. `synced_commit` 不是目标 commit 祖先（变基/改写）：报告风险，请用户选增量尝试或全量 `build`
6. 遗留 `modules/*/files/`：本轮不删、不停更以外的重写
7. 写完 `set-sync` + `validate`，changelog 追加本轮摘要

### maintain

用户点名改某一概念/实体/流/模块/切面/图/上下文/数据/表面/运行时/构建时：只改对应文件与相关 INDEX/链接，不触发全量重写。点名某个源文件：按当前 `detail_level` 更新该模块文件表；只有用户明确要详注或该文件属于选定的重要文件范围时才建或改 `notes/<path>.md`。若代码已变，先 `diff` 再按 [routing.md](references/routing.md) 改，避免规格落后。需要新图或改图时走 [diagrams.md](references/diagrams.md)。

### status

只跑 `status`（需要版本细节时加 `git-info`）。不写文件。

## 完成时输出

```markdown
## Spec 镜像
- 项目：<name>
- 根：`<spec_root>`
- 粒度：concise | detailed
- 分支 / commit：<branch> / `<short-sha>`（非 git 则写无）
- 本轮：init | build | update | maintain
- 变更：<改了哪些层>
```

---

## Self-evolution

本 Skill 具备经验积累、评估与持续进化能力。目录（均相对本 Skill 根目录）：

```text
agents/skills/project-spec-mirror/
├── SKILL.md
├── examples/      # 经过验证的优秀执行案例
├── evals/         # 可验证成功标准
└── experience/    # 真实失败 / 成功 / 规律
```

不要为了自进化而破坏上文已规定的目标、流程、工具用法、输出与约束。

### Examples

执行复杂任务前：

1. 检查 `examples/`
2. 找到与当前任务相关的成功案例
3. 优先复用已经验证的方法

没有相关案例时按上文正常执行，不要编造案例。

### Evaluation

任务完成前：

1. 检查相关 `evals/`
2. 验证关键输出
3. 检查是否违反 Skill 约束
4. 尽可能运行相关 Eval Cases（见 `evals/cases.yaml`）

优先确定性 Eval；无法确定性判断时再用 LLM Judge。Eval 失败则先修输出，不要带着失败交卷。

### Experience

任务完成后，出现以下情况才写入 `experience/`：

- 失败
- 用户纠正
- 明显成功
- 新的有效执行方法
- 可复用的经验

不要记录 trivial information。不要伪造条目。密钥、内部 URL、凭据不得写入。

单次失败 → `experience/failures/`。重复出现的规律 → `experience/patterns/`（至少两次同类证据）。

### Evolution

只有当 Experience 暴露出**可复用、稳定的问题或模式**时，才考虑修改本 Skill。

遵循：

```text
Experience
    ↓
Repeated Pattern
    ↓
Improvement Proposal
    ↓
Eval
    ↓
Pass
    ↓
Update Skill
```

禁止：

```text
Single Failure
    ↓
Directly modify SKILL.md
```

进入 Skill 正文的 Experience 必须同时满足：可复用于多个类似任务、有足够证据、能明确改善结果、不破坏已有能力、可通过 Eval 验证。一次性特殊情况只留 Experience，不改 Skill。

实际更新生产 `SKILL.md` 时：

1. 不要直接覆盖原文；记录 version / change / reason / evidence / evaluation。有 Git 则优先靠 Git diff 留历史。
2. 若改动来自**真实执行经验**：优先委托 `skill-evolver`（`evolutions/` → 验证 → 晋升），不要本 Skill 自己改生产稿。
3. 若只是结构/规则的显式修订且环境有 `skill-upgrader`：走其 `update` 模式（`agents/skills/project-spec-mirror/patches/`），仍须先提案再应用。
4. 未展示 Proposal 并获得用户确认前，不改生产 Skill。
