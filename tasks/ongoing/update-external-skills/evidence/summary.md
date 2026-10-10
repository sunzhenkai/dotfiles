# update-external-skills — 交付摘要

**完成判据**：见 `wizard/plan.md`（三件事齐备）。
**判定**：PASS

## 三步结果

| 步骤 | 命令 | 退出码 | 关键产物 |
|---|---|---|---|
| 1. 重锁 | `make skills-lock-update` | 0 | `wrote agents/skills.lock.yaml sources=2 blocked=2` |
| 2. 真变判断 | `python3 src/agents/lock_verify.py changed` | 0 | `changed_content=1 changed_revision_only=21 added=0 removed=0` |
| 3. 编目自检 | `make registry validate` | 0 | `✓ 注册表校验通过（strict-handlers）` |

完整证据：
- `lock-update.log`（535 行；首段 `==> lock-update https://github.com/sunzhenkai/solo-skills  2d8ae05cb63d → 072ef69647bd  (22 skills)`）
- `changed.txt`
- `registry-validate.txt`

## per-source 变更

| source | 状态 | 推进 | 备注 |
|---|---|---|---|
| `sunzhenkai/solo-skills` | 推进 | `2d8ae05c → 072ef6964`（22 skills） | 通过；1 条内容真变（`skill-evolver`），21 条纯 revision 推进 |
| `sunzhenkai/ui-templates-skill` | 部分推进 | — | 写入了 `ui-template-apply` / `ui-template-design`；`ui-template-author` 留在旧 `0d94a51f4f8e`（blocked） |
| `tt-a1i/archify` | 旧 revision | 留在 `69cf67208728` | blocked：19 BLOCK + 131 WARN |
| `mattpocock/skills` | current | — | 上游未动 |
| `zarazhangrui/frontend-slides` | current | — | 上游未动 |
| `solo-kingdom/senv` | current | — | 上游未动 |
| `humanlayer/skills` | current | — | 上游未动 |
| `Leonxlnx/taste-skill` | current | — | 上游未动 |
| `ibelick/ui-skills` | current | — | 上游未动 |

仅 `solo-skills` 与 `ui-templates-skill` 两个 source 真在本次写入锁文件 → `sources=2` 与脚本输出一致。

## 阻断（blocked）定性 — 步骤 1.5 输出

两条 skill 留在旧 revision，逐条给出证据与处置。

### archify（19 BLOCK / 131 WARN）

阻断规则类别：

| 规则 | 命中 | 原文样本 | 误报类型 | 处置 |
|---|---|---|---|---|
| `hardcoded_secret` | 多 | `var token = relationshipTokenGeometry(...)`、`const token = preparedCacheDirectories.get(...)` | 变量名含 `token` 是几何/缓存键的语义名，非凭据 | 走子任务改审计规则精度 |
| `jailbreak_role` | 多 | `// the same "omit locale, disclose the fallback" contract as before`、`Same default-canvas contract as lifecycle: 920x760 ...` | 注释里出现「contract」「disclose the fallback」「same as」等普通英文措辞，被当 jailbreak 模式 | 同上 |
| `bypass_approval` | 1 | `test('visual-check disables the Chrome sandbox only for root or an explicit environment opt-in', ...)` | 测试断言本身在写「必须显式 opt-in 才能关沙盒」，是反向语义 | 同上 |

证据：详见 `lock-update.log`（archify 段）。

### ui-template-author（52 BLOCK）

阻断规则类别：

| 规则 | 命中 | 原文样本 | 误报类型 | 处置 |
|---|---|---|---|---|
| `hardcoded_secret` | 52（全在一文件） | `catalog/workbench-shell/apply/01-token-map.yaml` 内 `project_token: --wt-color-app-shell` 等字段 | 该文件是设计系统语义令牌 → CSS 变量名映射表的字段名（`project_token`），非凭据；这是已知 case（archify 同款） | 同上 |

`ui-template-apply` / `ui-template-design` 通过，因此整 group 没有「全员 blocked」式拦死，仍写入了部分。

## 不在本次交付的口子（原文照搬，等用户决定）

skill 正文「收尾」段给出的下一步动作：

```bash
# 1. 下发本机（重取全部锁内条目并重写，实测分钟级；见坑 4）
bin/dotf agents -c --yes
# 2. 下发之后才有意义的核对：上游哈希 + 三个 layout 的已装副本
make skills-verify
# 3. 提交（仓库惯例：agents: ... 风格；registry validate 已过）
git add agents/skills.lock.yaml && git commit
```

三条都是流程**外**动作，按 AGENTS.md 与 taskrail 契约未经点名不执行；用户本轮只答「更新外部 skills」，对应范围到「锁推进 + 真变判断 + 编目自检」为止。

## 推荐下一步（用户决定）

| 动作 | 触发条件 | 耗时估计 |
|---|---|---|
| 改审计规则精度的子任务（archify / ui-template-author） | 想让锁推进到这两个 source 的 HEAD | 走 skills-store 三件套 |
| 重锁后再跑一次（验证 blocks 解除） | 上一步完成后 | 1 次 `make skills-lock-update` |
| `bin/dotf agents -c --yes` 下发本机 | 已决定接受变更面 | 约 390s（坑 4） |
| `make skills-verify` 三 layout 核对 | 下发完成后才有意义 | 1 次 `make skills-verify` |
| `git commit` | 想把锁变更入仓 | 1 次提交 |
