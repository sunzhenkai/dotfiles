---
name: dotf-code-review
description: 使用 OCR 兼容的代码审查 CLI，审查指定 Git 仓库的未提交改动、相对默认分支的 diff，或 GitLab/GitHub Merge Request / Pull Request；完整结果写入 review workspace 的 docs/reviews/{日期}/{change-name}，对话只打印按 P0~Pn 排序的总结。在用户要求 code review、审查 MR/PR、评审未提交改动时使用。
license: MIT
---

# dotf-code-review

用 OCR 兼容的 CLI 做 **Git diff 级代码审查**。机械步骤走 `scripts/reviewctl.py`；审查引擎使用已配置的 `ocr` 命令，不要用通用 agent 逐文件替代。

不替代：架构评审、岗位视角评审、需求/规格符合性评审。默认只审查、不改代码。

## 调用

```text
/dotf-code-review repo=<仓库名|仓库路径> [mode=uncommitted|default-branch] [change-name=<slug>]
/dotf-code-review <GitLab/GitHub MR 或 PR URL>
```

可选：业务背景（commit/MR 说明、需求一句话）→ 传给 `ocr --background`。

## MUST 先读取并执行

1. 本文件全文。
2. 机械命令用 [`scripts/reviewctl.py`](scripts/reviewctl.py)，`--root` 指向审查 workspace 根目录。

```bash
python3 <skill-root>/scripts/reviewctl.py --root <workspace-root> inspect --repo <name-or-path>
python3 <skill-root>/scripts/reviewctl.py parse-mr --url '<url>'
python3 <skill-root>/scripts/reviewctl.py write --ocr-json /tmp/ocr.json --meta-json /tmp/meta.json
```

## 前置

```bash
which ocr || echo "NOT INSTALLED"
ocr llm test
```

未安装：按 OCR CLI 的上游文档安装（先征得用户同意）。`ocr llm test` 失败则停下来，让用户配置 LLM（环境变量或 `ocr config`），**禁止编造 API key**。

GitLab 自建实例认证：

- 优先使用环境变量 `GITLAB_TOKEN`，不要把 token 写入命令行参数、日志或审查产物。
- 调用 `glab` 时映射为：`GITLAB_TOKEN="$GITLAB_TOKEN" glab ...`；GitLab API 需要 token 具备 `api` scope。
- 若 `GITLAB_TOKEN` 未设置且目标需要认证，停止并请用户配置该变量；禁止编造或输出 token。

## 流程

### 1. 解析目标

- 用户给了 **MR/PR URL** → 走「MR 模式」，忽略本地脏工作区。
- 用户给了 **仓库名或路径** → `reviewctl inspect`。
- 都没给：若当前对话已点名仓库则用之；否则询问。多命中时列出 `candidates` 让用户选。

### 2. 确定审查范围（确认门）

**仓库模式**（`inspect` 的 `recommendation`）：

| recommendation | 含义 | 下一步 |
|---|---|---|
| `uncommitted` | 仅工作区脏 | 建议 workspace 审查；**仍须用户确认** |
| `default-branch` | 干净且相对默认分支有提交 | 建议 `--from <comparison_ref> --to HEAD`；**仍须用户确认** |
| `ask` | 既有未提交又有分支提交 | **必须**让用户选其一，禁止默默合并两种 diff |
| `nothing` | 干净且无新提交 | 停止，问是否改用 MR 链接或其它 ref |

用户已显式给 `mode=` 时，不再改推荐，仍要先 `ocr review --preview` 展示文件列表再跑 LLM。

**MR/PR 模式**：

1. `reviewctl parse-mr --url ...` → `kind` / `host` / `project` / `iid` / `repo_hint`
2. 用 `repo_hint`（或 URL 里的 project）`inspect`/`resolve-repo` 定位本地仓；找不到则列出候选或请用户给仓库路径。
3. 取源/目标分支：
   - GitLab：`GITLAB_TOKEN="$GITLAB_TOKEN" glab mr view <iid> --repo https://<host>/<project> -F json`
   - GitHub：`gh pr view <iid> --repo <project> --json baseRefName,headRefName,title`
4. **只 fetch，不 checkout、不 stash**：

```bash
git -C <git_root_abs> fetch origin
# GitLab
git -C <git_root_abs> fetch origin "merge-requests/<iid>/head:refs/code-review/mr-<iid>"
# GitHub
git -C <git_root_abs> fetch origin "pull/<iid>/head:refs/code-review/pr-<iid>"
```

5. 审查范围：`--from origin/<target_branch> --to refs/code-review/mr-<iid>`（GitHub 用 `pr-<iid>`）
6. `ocr review --preview` 后确认再跑 LLM。

### 3. 跑 ocr

始终：`--audience agent --format json --repo <git_root_abs>`，有背景就加 `-b`。stdout 重定向到文件，禁止 `head`/`tail` 截断。

```bash
# 未提交
ocr review --audience agent --format json --repo <abs> -b "<background>" > /tmp/ocr.json 2>/tmp/ocr.err
# 相对默认分支 / MR / PR
ocr review --audience agent --format json --repo <abs> -b "<background>" \
  --from <from> --to <to> > /tmp/ocr.json 2>/tmp/ocr.err
```

先看 exit code 与 `/tmp/ocr.err`。JSON `status=skipped` 视为无审查对象，不是失败。

### 4. 分级并落盘

读取 ocr JSON 的 `comments[]`，为每条指定 `priority`：`P0`（发布阻断 / 安全 / 数据损坏）· `P1`（应尽快修的缺陷）· `P2`（普通缺陷）· `P3`（低影响仍值得修）。可先用 `reviewctl` 启发式，**有把握时覆盖**。把带 `priority` 的 comments 写回临时 JSON。

`change-name`：用户指定优先；否则 `reviewctl change-name`。日期使用运行当天的 `YYYY-MM-DD`。

```bash
python3 <skill-root>/scripts/reviewctl.py --root <workspace-root> write \
  --ocr-json /tmp/ocr.classified.json --meta-json /tmp/meta.json
```

`meta.json` 至少含：`repo`、`mode`、`date`、`change_name`、`branch`、`from`、`to`、`default_branch`；MR/PR 再加 `mr_url`、`mr_iid`、`title`。

产物目录：`<workspace-root>/docs/reviews/{YYYY-MM-DD}/{change-name}/`

| 文件 | 内容 |
|------|------|
| `ocr-raw.json` | ocr 完整 JSON |
| `review.md` | 完整审查（含现有代码 / 建议 / 推理） |
| `summary.md` | 总结版（同对话打印） |

并更新 `docs/reviews/INDEX.md`。

### 5. MR/PR 评论确认门

仅在 **MR/PR 模式** 且 `review.md` 已成功落盘后，询问用户：

> 完整 review 报告已保存到 `<review.md 路径>`。是否将该完整报告作为评论发布到 `<MR/PR URL>`？这会对远程平台产生写操作，请确认目标和内容。

在用户明确确认前，禁止调用 `glab mr note`、`gh pr comment` 或任何等效的远程写接口。确认时再次核对目标 URL/IID 与待发布文件；用户拒绝、未确认或目标不明确时，只保留本地报告，不发布评论。用户确认后，以 `review.md` 的完整内容发布一条评论，并在结果中报告成功或失败。仓库模式不询问，也不发布评论。

### 6. 对用户只打印总结

对话输出 **仅** `write` 返回的 `summary`（已按 P0→Pn 排序），再给完整文档路径。不要把 `thinking`、大段代码、原始 JSON 贴进对话。无 findings 时打印 `No findings.` + 文档链接。

## 边界

- 默认不改业务代码、不 commit、不 push、不在 MR/PR 上发评论；远程评论必须经过上一步的明确确认。用户明确要求「顺手修」才可改代码。
- 不 `checkout` / `stash` / `reset` 目标仓；MR/PR 只用 fetch 的 `refs/code-review/*`。
- 完整结果只写 `--root` 指定 workspace 的 `docs/reviews/`，不写目标仓的代码目录。
- 架构评审、岗位视角评审、需求/规格符合性评审分别使用适合的专门流程。
