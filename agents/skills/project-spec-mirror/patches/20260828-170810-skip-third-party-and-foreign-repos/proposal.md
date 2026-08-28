# 只整理本工程代码，跳过三方依赖与外来仓

- target: agents/skills/project-spec-mirror
- patch: 20260828-170810-skip-third-party-and-foreign-repos
- risk: medium
- status: proposed

## Intent

镜像只覆盖当前 `--source` 工程自己的代码。Agent 与 `inventory` / `diff` / `route` / `symbols` 都跳过三方依赖源码，以及本工程所依赖的其他仓库代码。

跳过范围：

- 包管理器安装树：`vendor/`（Go、PHP Composer 等）、`node_modules/`、虚拟环境，以及同类目录。
- 树内嵌套 git / submodule，以及 `replace`、Composer path、同级克隆等外来仓源码。

仍允许：在 `context/` 记邻接系统边界；在 `build/` 列包名与影响运行的约束。给那个仓做镜像必须另开一次会话并显式 `--source`。

非目标：不改变放置规则；不把 `deps/`、`third_party/` 等可能属于本工程的目录名一律忽略；不自动 commit。

## Conflict check

- 收紧 `layout.md`「第三方默认不进 modules，除非处理线必须引用」：改为不把对方源文件列入文件表，只允许写包名/接口/邻接。这正是本次要改的过宽例外。
- 与外来仓放置（`spec/<project>/` + `--source`）不冲突：那是用户显式给另一工程建独立镜像，不是在本镜像里吞掉依赖仓。
- 与 `build/`「第三方库只列约束」一致，只是把「不要打开对方源码」写死。
- `vendor` / `node_modules` 已在忽略目录中；本次补上 diff/route 过滤与嵌套 git，避免 update 把它们当 `unmapped`。

## Rationale

规格孪生的阅读单位是本工程如何运行与如何改。Vendored 树和依赖仓是别人的实现，写进本镜像会膨胀、过期、并抢走模块划分。规则跨语言成立，可用 inventory/diff 测试验证。

## Files

- `SKILL.md` — 非目标与 inventory/diff 说明
- `references/layout.md` — 模块边界不含三方/外来仓源码
- `references/routing.md` — 已忽略路径不得当 unmapped
- `references/projections.md` — build 依赖不打开 vendor/外来仓
- `references/facets.md` — SOURCE 不含三方/外来仓源码
- `scripts/specctl.py` — 忽略目录、嵌套 git/submodule、diff/symbols 过滤
- `tests/test_specctl.py` — vendor/diff/嵌套仓回归
- `evals/cases.yaml` — 边界 case

## Validation

- 应用前：`git apply --check --recount` 本 patch
- 应用后：`git diff --check -- agents/skills/project-spec-mirror`；`python3 -m unittest discover -s agents/skills/project-spec-mirror/tests`
- frontmatter `name` 与目录名一致；引用路径存在；无私有信息
