# 增加可恢复可运行系统的顶层投影

- target: agents/skills/project-spec-mirror
- patch: 20260828-160733-recovery-projections
- risk: high
- status: proposed

## Intent

把镜像验收从「读清楚 + 按切片改/迁/验」抬到档 C：只凭镜像能重建可运行系统。新增五个顶层投影，并收紧 VERIFY/TRAFFIC，使单实现项目也不再把这两层写成「不适用」了事。

新顶层（目录名固定）：

| 目录 | 回答 |
|------|------|
| `context/` | 系统在环境里的位置：actor、邻接、协议、信任、质量属性、安全边界 |
| `data/` | 持久化与一致性：存储实例、与实体的差、迁移、保留 |
| `surface/` | 必须对上的对外表面；`config.md` 是配置键表 |
| `runtime/` | 进程、部署、网络、启动顺序、健康检查、故障弹性 |
| `build/` | 工具链、构建/测试/迁移/启动配方，用于再生可运行系统 |

非目标：不抄源码或测试正文；不把密钥/配置值写入镜像；不新增 security/quality 顶层（作为 `context/` / `runtime/` 必填节）；不把 `facets/contracts/runtime.md` 改名；不实现业务代码；不自动 commit。

## Conflict check

- 与 `layout.md`「不要在金字塔和切面/图表之外再造顶层分类」冲突：改为「顶层仅限本文件列出的目录」，把恢复投影与金字塔、切面、图表并列。
- 与「不代替 README」不冲突：`build/` 是可再生配方（命令、产物、依赖），不是项目对外介绍。
- 与现有 `facets/contracts/runtime.md`：后者仍是指标/灰度/回滚条件；拓扑与启动改走 `runtime/`。
- 与 SOURCE：配置文件仍是证据路径；键语义与环境差改走 `surface/config.md`。
- 与实体：实体仍是领域对象；库表/迁移/一致性走 `data/`。
- 已有镜像：update 先补骨架，不删金字塔；`validate` 将要求新 INDEX（及 `surface/config.md`）存在。

## Rationale

档 C 需要上下文、数据面、对外表面、运行拓扑和构建配方五者同时在场，否则只能恢复「源码树讲义」。五个顶层与现有金字塔/切面正交，跨项目仍成立；`validate` 与 init 骨架可机械检查；恢复完备自检可在 build 结束时核对。

## Files

- `SKILL.md` — 描述、build/update/maintain 纳入恢复投影
- `references/layout.md` — 目录、阅读顺序、README/overview 模板
- `references/projections.md` — 五层规则与恢复自检（新）
- `references/modes.md` — 简约/详尽如何写深新层
- `references/knowledge.md` — 交叉链接自检
- `references/facets.md` — 区分 runtime 契约；收紧 VERIFY/TRAFFIC
- `references/diagrams.md` — 上下文/部署图
- `references/routing.md` — compose/schema/env/CI 等路由到新层
- `scripts/specctl.py` — 骨架、README/overview、validate 必填文件
- `tests/test_specctl.py` / `tests/test_skill_contract.py`
- `evals/cases.yaml`

## Validation

- 应用前：`git apply --check --recount` 本 patch
- 应用后：`git diff --check -- agents/skills/project-spec-mirror`；`python3 -m unittest discover -s agents/skills/project-spec-mirror/tests`
- frontmatter `name`/`id` 与目录名一致；引用路径存在；无私有信息
