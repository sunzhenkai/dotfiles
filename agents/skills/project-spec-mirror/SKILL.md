---
id: project-spec-mirror
name: project-spec-mirror
description: >-
  创建或增量维护给人读的 project spec 镜像，包含金字塔、适用的恢复投影与工程切面，
  支持 concise/detailed 及代码证据粒度；Git 源按 commit 更新，非 Git 源按 coverage 对照文件表。
  在用户要求 project spec 镜像、spec 孪生、可读规格目录、工程切面或恢复项目运行知识时使用。
  不用于 OpenSpec change、实现代码或只读问答；用户要求图表时委托 archify。
compatibility: Requires Python 3.10+; Git is required for commit-diff updates. Requested diagrams additionally require Node.js and an installed archify skill.
---

# Project Spec Mirror

面向用户默认使用简体中文。命令、路径、代码、标识符与既成术语保持原文。

为目标 project 维护给人读的规格孪生，不是实现契约、不是源码副本。机械工作只通过 `specctl`；金字塔、恢复投影、切面正文由 Agent 撰写。验收目标：只凭镜像能重建该项目**实际具备**的可运行能力；不适用能力要有证据地标明。用户明确要求结构图、流程、时序、数据流或状态机时，委托 skill `archify`（[tt-a1i/archify](https://github.com/tt-a1i/archify)），产物放 `diagrams/`。

```bash
SPECCTL=$(command -v specctl || echo "python3 <this-skill>/scripts/specctl.py")
$SPECCTL <command> ...
```

stdout 只输出 JSON，stderr 是一行摘要。退出码：**0** 成功，**1** 硬失败，**2** 需要用户确认。看到 2 就原样报告 `prompt` / `confirm_args`，等用户明确同意后再带上 CLI 给出的参数重跑，不得自行扩大范围。

## 非目标

- 不是 OpenSpec / `openspec/` / 实现 change；不要把镜像写进那些目录。
- 不修改目标 project 的源码、测试、构建或依赖。
- 不代替 README 成为项目对外文档；镜像服务「给人把项目读清楚」。
- 不自动 commit / push；不把密钥、`.env`、凭据或源码里的密钥字面量写进镜像。
- 默认不把每个源文件做成规格页；文件主要作为清单行、路由键和证据路径。
- 不把 `modules/<m>/notes/` 退化为 "一文件一详页"；topic notes（易踩坑的概念）与源文件级 `notes/<source-rel>.md` 并列。后者仅热点清单约束；前者在 `detail_level=complete` 下必建，其余模式仅用户明确接受维护成本后才建，不把它误称为默认 detailed 行为。
- 不整理三方依赖源码，也不整理所依赖的其他仓库的代码；镜像只覆盖当前 `--source` 工程自己的代码。外来仓只在 `context/` 记邻接协议，在 `build/` 点到包名与版本约束。
- 只梳理文本文件。`inventory` / `diff` / `route` / `symbols` 共用同一条输入边界，具体跳过哪些路径见 [routing.md](references/routing.md)。

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

未点名阶段时按现状推断，并用一行说明：无镜像 → `init`；`build_status=skeleton` → `build`；`build_status=built` → `update`；只改某一词条 → `maintain`。旧镜像缺字段时，有 `synced_commit` 视为 built，否则视为 skeleton。

| 阶段 | 做什么 | 先读 |
|------|--------|------|
| `init` | 探测、确认、写骨架 | 本文件 |
| `build` | 按粒度生成金字塔 + 恢复投影 + 切面 | [layout.md](references/layout.md)、[modes.md](references/modes.md)、[knowledge.md](references/knowledge.md)、[projections.md](references/projections.md)、[facets.md](references/facets.md)、[diagrams.md](references/diagrams.md)、[routing.md](references/routing.md) |
| `update` | 用 git diff 把变更文件路由到已有页 | 同上，只加载受影响层 |
| `maintain` | 改概念/实体/流/模块/切面/图/恢复投影中的指定条目 | 对应 reference |
| `status` | 只读同步状态 | 本文件 |

同一时刻只维护**一个 active target** 和一个 `spec_root`。用户要求批量项目时可顺序处理：完成并汇报当前 target 后重新 `detect` 下一个；禁止在一次写入步骤中混用两个项目的状态或输出目录。

## specctl

| command | 用途 |
|---------|------|
| `detect` | 判定 project 根、放置方式、是否已有镜像 |
| `init` | 建目录骨架与 `.mirror.json`；缺确认时退出 2 |
| `status` | 镜像状态 + git 新鲜度 |
| `inventory` | 源文件清单（已忽略构建产物、密钥、三方安装树与外来仓） |
| `symbols` | 从代码文件提取函数/类型/变量候选，供详尽模式核对行为承载符号；不作为完备证明 |
| `git-info` | 是否 git、默认分支、指定分支的 commit |
| `diff` | 相对 `synced_commit`（或 `--from`）的文件级变更（同样忽略三方/外来仓） |
| `coverage` | 对照 `inventory` 与模块「文件」表：`missing` / `extra` / `unscoped` |
| `route` | 把 `diff` 的文件映射到模块 README（文件表 / 根前缀 / unmapped / rename） |
| `set-sync` | 正文写完且骨架校验通过后回写 build 状态、commit / branch / mode / scope / hotspots / 时间，并同步 README 状态表 |
| `finalize` | 收尾一条命令：先按本轮粒度跑 coverage 门禁，通过才回写状态，再复验骨架 |
| `validate` | 金字塔、恢复投影、切面骨架与 `.mirror.json` 完整性 |

完整参数以 `$SPECCTL <command> --help` 为准。常用全局：`--cwd`、`--spec`、`--source`、`--project`、`--branch`。

## 公共执行契约

1. 任何写入阶段都先 `detect`（或 `status`）。不要手建目录绕过 `init`。
2. 自然语言、分层叙述、交叉链接由 Agent 完成。CLI 不写概述、不抽概念、不编流程。
3. 目标是 git 仓库时：默认跟踪**默认分支**（`origin/HEAD` → `main`/`master` 回退）。用户指定 `--branch` 则记录该分支的 commit，而不是随意的工作区 HEAD。
4. 非 git 源：仍可 init/build/maintain；完成 build 后用 `set-sync --built` 写 `build_status=built`，不得伪造 commit；`update` 不能做 commit diff，改为跑 `$SPECCTL coverage` 对照文件表并说明限制。
5. 更新时保留 `<!-- manual -->` … `<!-- /manual -->` 块，不得覆盖。
6. 发现密钥形态内容：镜像里写 `<REDACTED>`，并在输出中说明省略，不把原文抄进 spec。包括源码常量/字段里的 `AppKey`、`SecretKey`、AccessKey、token、password、私钥、连接串等**值**；可以写「存在某鉴权字段、从何处注入」，禁止把赋值抄进文件表、核心符号或配置说明。非机密的产品标识（如 `appId`）可以写；值若像随机密钥、长 hex/base64 或口令，仍按密钥处理。
7. 核对模块文件表覆盖必须跑 `$SPECCTL coverage`，不要手对 `inventory`。只要求代码文件（`CODE_EXTS`）出现在「文件」表；配置/CI/compose 等走恢复投影。`detailed` 且 `important`/`complete` 时 `enforce` 为真，`missing` 必须清空才能 `set-sync`。concise / lightweight 把 `missing` 当提示。文件表可用精确路径或目录范围。

## 工作流

### init

1. `$SPECCTL detect`
2. 没有镜像 → `$SPECCTL init ...`（不要先加 `--confirm`）
3. 退出码 2：向用户展示 `prompt` 与将创建的 `spec_root` / `source` / `placement`，得到明确同意后用返回的 `confirm_args` 重跑
4. 成功后只存在骨架，接着进入 `build`，不要把空目录当成已完成

### build

1. `$SPECCTL status` 与 `$SPECCTL inventory`；详尽模式先确认 `detail_level`（默认 `important`）。important 还要明确将写深的源相对路径或前缀；对这些路径及 complete 中的行为代码按需跑 `symbols`，再结合源码核对行为承载符号。候选为空或不完整时如实说明，不声称方法全集完备；测试文件不逐方法抽取
2. 读 [layout.md](references/layout.md) 按金字塔写正文；粒度见 [modes.md](references/modes.md)
3. 识别项目实际能力并维护恢复投影（上下文、数据、表面、运行时、构建），见 [projections.md](references/projections.md)。适用层写到可恢复；不适用层保留 INDEX 并写判断证据。结束前做恢复完备自检
4. 识别并维护概念、实体、业务处理线，见 [knowledge.md](references/knowledge.md)
5. 识别并维护适用的工程切面（来源、契约、切片、验证、流量），见 [facets.md](references/facets.md)。切片不必等全部契约写完；先 identified / characterized 再补 specified。VERIFY 至少写现有测试/性质；完全没有部署或流量切换能力时，TRAFFIC 写 `不适用` 与证据，不编发布方案
6. 按 [diagrams.md](references/diagrams.md) 为复杂业务逻辑和用户点名的图本轮交付 archify HTML。主处理线若有分叉、状态机或跨模块时序，必须有图并链到 `diagrams/`。线性三步用列表即可。缺 archify 时把必配图列为未完成，禁止假 HTML 或占位
7. 每个模块 README 都要有「根」表与「文件」表（[routing.md](references/routing.md)）。下一轮 update 靠这两个标题把变更文件路由到页，缺一个这个模块就只能重建
8. 详尽模式选定一种 `detail_level`，文件表按它覆盖：`complete` 覆盖全部 inventory 文件并深入行为承载符号；`important`（默认）覆盖范围内文件，对显式 important 路径写深，其余简述；`lightweight` 只保留必要代码证据，领域、流程、契约与投影照样加深。测试只写覆盖意图，不展开方法步骤。三档细则见 [modes.md](references/modes.md)
9. 用户要「每个文件一页」时先说明模块 README 才是阅读单位，再问他要的是 `complete` 还是某几处热点；要源文件级热点详注却没给路径时同样先问（建议切片入口或分批），没谈拢就不批量建源文件级 `notes/`。遗留 `modules/*/files/` 停更、不删，在模块 README 注明可能过期。本工作区若已有其他项目的镜像，先扫一眼它们的 `modules/*/notes/` 主题列表对齐维度（只看主题，不复制内容），省得每个仓从零想选题
10. **`detail_level=complete` 必建 `modules/<m>/notes/` 详注**，不是 opt-in：跨文件契约、易踩坑的设计选择、监控盲区等"读源码看不出来"的内容落到 notes/ 而不是塞进模块 README。按 [modes.md](references/modes.md) 的"5 类触发条件"清单枚举，每个模块挑 ≥1 类、整体 ≥5 篇。命名是 topic（易踩坑的概念）而非源相对路径
11. 写完文件表后跑 `$SPECCTL finalize` 收尾（不要手对清单）：它先按本轮粒度做 coverage 门禁，`enforce` 为真且有 `missing` 就停在这一步并列出缺哪些文件；通过后回写 build 状态并复验骨架与 README 状态表。Git 源 `$SPECCTL finalize --commit <id> --branch <name> --mode <concise|detailed>`，非 Git 源去掉 `--commit`。只有 detailed 才加 `--detail-level <complete|important|lightweight>`（默认 `important`）；important 对每个选定路径重复传 `--important-path <path>`，有热点则加 `--hotspot`。需要分步排查时仍可单独跑 `$SPECCTL coverage` / `set-sync` / `validate`
12. 向用户给出镜像根路径、怎么读（先 overview，再恢复投影，再切面/金字塔）、同步 commit

### update

1. `$SPECCTL status` 与 `$SPECCTL route`（内部用与 `diff` 相同的 `synced_commit..目标分支 commit`；可加 `--from` / `--to`）。按返回的 `modules` / `pages` / `renames` / `unmapped` 改页，不要手算、不要绕过 `route`
2. 只改映射到的模块 README 与跟链接的概念、实体、处理线、恢复投影、切面与相关图；rename（`status=R`）改文件表路径，不当删+增。上层概述若结论变了才改
3. 若缺 `context/` `data/` `surface/` `runtime/` `build/`、`facets/` 或 `diagrams/` 骨架，先补 INDEX（及 `surface/config.md`、切面短页），再改正文；不删已有金字塔
4. 工作区脏或当前分支与记录分支不一致：在输出中说明，仍以 `--branch`（默认默认分支）的 commit 为准，不要把未提交改动默认为已同步
5. `synced_commit` 不是目标 commit 祖先（变基/改写）：报告风险，请用户选增量尝试或全量 `build`
6. 遗留 `modules/*/files/`：本轮不删、不停更以外的重写
7. changelog 追加本轮摘要；改完文件表后跑 `$SPECCTL finalize`，参数与 build 收尾一致（Git 源带 `--commit`，非 Git 源不带）

### maintain

用户点名改某一概念/实体/流/模块/切面/图/上下文/数据/表面/运行时/构建时：只改对应文件与相关 INDEX/链接，不触发全量重写。点名某个源文件：按当前 `detail_level` 更新该模块文件表，再跑 `$SPECCTL coverage`；命中 `important_paths` 时写深模块页，但不会自动建立 `notes/`。只有用户明确要热点详注或该路径已在 `hotspots` 时才建或改源文件级 `notes/<path>.md`。若代码已变，先 `diff` 再按 [routing.md](references/routing.md) 改，避免规格落后。需要新图或改图时走 [diagrams.md](references/diagrams.md)。

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

## 质量检查

完成镜像任务前对照 [checklist.md](references/checklist.md) 核对本轮涉及的条目，并运行 `specctl validate`。任一条不满足就先修镜像输出再给回执，不要带着已知缺口声称完成。

`examples/`、`evals/`、`experience/` 与 `tests/` 只存在于本 Skill 的源仓库，安装到 agent 目录后不随行，所以运行现场能读到的自检表就是上面那份 checklist。维护本 Skill 自身时（改 SKILL.md、references 或 specctl）另外跑 `evals/cases.yaml` 的完整回归与 `python3 -m unittest discover -s <skill-dir>/tests`。普通镜像任务不写这些目录，也不自行修改本 Skill；只有用户明确要求维护 Skill 时才进入外部维护流程。
