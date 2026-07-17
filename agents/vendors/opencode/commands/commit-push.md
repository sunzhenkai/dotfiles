---
description: 分析 git 变更、创建 commit 并 push；大改动下避免通读巨型 diff
---

分析当前 git 变更，起草提交说明，创建 commit 并 push 到远程。

**Input**：可选说明（例如「只 commit 不 push」「消息侧重修复」）。默认 **commit + push**。

## 大改动耗时优化

**禁止** 默认通读整库完整 diff。先：

```bash
git status --short
git diff --stat
git diff --cached --stat
```

- 文件少且 diff 小：再按需看具体 `git diff -- <path>`
- 文件多或 stat 很大：按路径分组理解意图；只对核心文件抽样 diff；lockfile/生成物/大资源 **不读内容**
- 不要为写消息而打开大量文件或拉取上千行 patch

## 安全

- 不改 git config；不 force push main/master；不跳过 hooks（除非用户明确要求）
- 排除密钥与明显不该进库的文件
- 用 HEREDOC 写 commit message；路径级 `git add`

## 步骤

1. 用 status / diff --stat / log / branch -vv 摸清状态与风格（大改动优先 stat）
2. 确认暂存范围并 `git add -- <paths>`
3. `git commit`（HEREDOC 消息，1–2 句写清 why）
4. `git push -u origin HEAD`（除非用户只要 commit）
5. `git status -sb` 确认结果并简短汇报

详细约定见 skill `commit-push`。
