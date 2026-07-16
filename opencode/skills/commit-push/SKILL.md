---
name: commit-push
description: >
---

# Commit & Push

将当前工作区变更提交并推送到远程。默认执行 **commit + push**；若用户只要 commit 或只要 push，按其指示。

## 耗时优化（大改动必读）

大改动时 **禁止** 一上来对整库跑完整 `git diff` 并通读所有 patch。按下面顺序收敛上下文：

1. **先摸规模**（廉价命令，始终先跑）
   ```bash
   git status --short
   git diff --stat
   git diff --cached --stat
   ```
2. **按规模分流**
   - 变更文件 ≤ 15 且 `diff --stat` 总插入+删除线数不明显过大：可对相关文件看完整 diff
   - 文件更多或 stat 显示单文件/总量很大：
     - 用 `git diff --name-only` / `git status -sb` 按目录或类型分组理解意图
     - 只对 **核心逻辑文件** 抽样：`git diff -- <path>`（每次少量路径）
     - 对 lockfile、生成物、vendor、大 JSON/YAML、资源文件：**只看路径与是否应纳入提交，不读内容**
3. **硬限制**
   - 单文件 diff 过大（例如明显上千行）或疑似生成/二进制：不要 `Read` 文件全文，也不要拉完整 patch
   - 不要为了写 commit message 而并行打开几十个文件
   - 消息依据：**status + stat + 少量代表性 diff + 文件路径模式** 即可，不要求证明读过每一行
4. **暂存策略**
   - 大改动用路径级 `git add -- <paths>`，避免盲目 `git add -A` 带入无关或敏感文件
   - 先看 `git status` / untracked，排除 `.env`、密钥、大产物

## 安全协议

- **不要** 修改 git config
- **不要** 用破坏性命令（`push --force`、hard reset 等），除非用户明确要求
- **不要** 跳过 hooks（`--no-verify` 等），除非用户明确要求
- **不要** force push 到 `main`/`master`；若用户要求则警告
- **避免** `commit --amend`，除非用户明确要求且满足：HEAD 由你在本会话创建、尚未 push、amend 非因 hook 失败
- hook 失败：修问题后 **新建** commit，不要 amend
- 没有变更时不要空提交
- 疑似密钥文件（`.env`、`credentials.json` 等）不要提交；若用户点名要提交则警告

## 步骤

并行收集（大改动用 stat 变体，见上）：

```bash
git status --short
git branch -vv
git log -5 --oneline
git diff --stat
git diff --cached --stat
```

需要看远程是否需先 pull 时再：`git status -sb`（看 ahead/behind）。

### 起草说明

- 1–2 句，说明 **为什么**，不是文件清单
- 匹配仓库现有 log 风格（看 `git log`）
- 经 HEREDOC 提交，避免引号问题：

```bash
git add -- <paths...>
git commit -m "$(cat <<'EOF'
消息正文。

EOF
)"
```

### Push

```bash
git push -u origin HEAD
```

若无上游或被拒绝，说明原因并停下，不要强推。

### 收尾

- 再跑 `git status -sb` 确认干净或仅剩有意未提交项
- 简短告知：分支、commit 摘要、是否已 push

## 何时问用户

- 变更意图不清（多件事混在一起是否拆分）
- 包含可能不该提交的文件
- push 需要选择 remote/分支且无法从 tracking 判断
