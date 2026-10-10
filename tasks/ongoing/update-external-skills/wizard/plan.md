# 任务方案：更新外部 skills

## 目标
把 `agents/skills.yaml` 编目里三个第三方 group（`solo-skills` / `mattpocock` / `archify` / `ui-templates`，共 4 组）的 `agents/skills.lock.yaml` 推进到各 source 当前 HEAD，区分内容真变与纯 revision 前进，并校验仓库编目自洽（`make registry validate`）。

## 完成判据
`make skills-lock-update` 完成且 `blocked=0`（或 `blocked>0` 的每条已经在「步骤 1.5 阻断分类」中给出依据 + 处理路径），`python3 src/agents/lock_verify.py changed` 报告 `changed_content=N changed_revision_only=M added=A removed=R` 行被落账（可写盘于 `evidence_root/`），`make registry validate` 通过——三件事同轮齐备即视为完成。**不**含下发本机、git commit、git push。

## 交付标准
- `agents/skills.lock.yaml` 已推进到各 source HEAD（含 evidence / audit date 同步刷新）。
- `blocked` 字段（若有）逐条标注定性来源（审计命中规则 / 文件 / 行 / 是否为过宽规则误报 → 是否走 skills-store 三件套）。
- 变化分类报告（`changed_content` / `changed_revision_only` / `added` / `removed`）落仓外 `evidence_root/`。
- 新发现属「编目变更」（条目增删/改名）→「追加子任务」出口，不在本任务内。
- 本流程内**禁止**：`bin/dotf agents -c --yes`、`git commit`、`git push`，统一交下游。

## 前提
- 事实：仓库根有 `Makefile`、`agents/skills.yaml`、`agents/skills.lock.yaml`（下一步需查是否真存在）；`src/agents/lock_update.py` 与 `src/agents/lock_verify.py` 已就位；`.agents/skills/update-external-skills/SKILL.md` 与本任务同义。
- 假设：网络可达公网 git（github.com 的 sunzhenkai/solo-skills、mattpocock/skills、tt-a1i/archify、sunzhenkai/ui-templates-skill）；非 TTY shell 默认环境。

## 步骤
1. **盘点前提与现状**：确认 `agents/skills.lock.yaml` 存在；记录每个 source 的当前 revision 与上游 HEAD 的差（只统计，不重锁），落 `evidence_root/pre-heads.txt`；判定上轮提交时间，作为后续变化幅度的初判。验证：`test -f agents/skills.lock.yaml` 且 `evidence_root/pre-heads.txt` 已落盘。
2. **重锁（步骤 1）**：`LOG=$(mktemp /tmp/skills-lock-update-XXXX.log) && make skills-lock-update 2>&1 | tee "$LOG"`。落地：`make` 末尾的 `wrote agents/skills.lock.yaml sources=N blocked=M` 行与每个 source 的 `current`/`promoted` 标签。若 `blocked=0` 直接进步骤 3；若 `blocked>0`，按 SKILL「blocked>0」分支从 `$LOG` 读上方汇总（不再取上游），逐条定性 → 写 `evidence_root/blocked-classification.md`。
3. **步骤 1.5（仅当 blocked>0 才执行）**：判定分类——
   - 真误报（例：`jailbreak_role` 命中 MIT 套话导致 archify 每轮被卡）：走入 `skill-evolver` / 单独任务「改审计规则」，**不**就地放行。
   - 真违规：保留旧 revision；记录原因。
   - 上游改名/缺目录 → 编目变更 → 转子任务（详见 SKILL 坑 12），**不**就地补种子。
   验证：`evidence_root/blocked-classification.md` 每条都有「规则 / 文件:行 / 命中原文 / 处置」四栏。
4. **判断内容真变（步骤 2）**：`python3 src/agents/lock_verify.py changed`，输出整体留存到 `evidence_root/changed.txt`；统计 `changed_content / changed_revision_only / added / removed`；`N=0` 且无 add/remove 也属合法结局（纯重钉）。验证：`evidence_root/changed.txt` 含计数行 + 完整明细（非 `tail -40` 切尾）。
5. **校验仓库产物（步骤 3）**：`make registry validate`，过则具备提交条件——但 commit 不在本任务。验证：exit 0，输出无 `error`/`fail`。
6. **写交付摘要**：落 `evidence_root/summary.md`（含 pre/post revision、`blocked` 分类、变化计数、recommend 提交窗）；更新 `TASK.md` 与 `tasks/INDEX.md`；把「下发/提交/推送三连」原样作为后续提示移交用户，未授权前不执行。

## 阻塞点
- **公网不可达 / 代理拦截**：`git fetch` 失败会让 `make skills-lock-update` 在 source 段落直接报错；处理：本会话停下问「是否走代理 / 切 mirror？」——属线上行为，未经授权不动。
- **非 TTY 默认 fail / `--yes` 缺失**：`make skills-lock-update` 自身不需要，但 skill 正文给的「下一步清单」里的 `bin/dotf agents -c --yes` 必须显式带 `--yes`；本任务**不**跑那一步，故不受影响——这点留在「要点」里提醒下游。
- **审计脚本命中过宽规则（例 archify 的 MIT LICENSE 套话）**：见步骤 1.5；不在本任务就地改规则、不就地放行，转子任务。

## 坑 / 注意事项
- **步骤 1 的输出必须整体留存**：禁止「`make skills-lock-update | tail -60`」一类管道；用 `tee "$LOG"` 与 `tail "$LOG"` / `grep "$LOG"`（SKILL 坑 16）。重跑一次重锁 = 多一次网络往返 + 大文件扫描。
- **步骤 2 的输出也别 `tail -40`**：会被迫重跑。`grep 'content+revision'` 挑读（SKILL 坑 16）。
- **不重钉「先看上游」**：禁止「先单独 fetch 看 HEAD」一类前置动作；只对历史记录做一步方法学统计可以（步骤 1 之前），重钉前的网络取只走 `make skills-lock-update`（SKILL 流程注解）。
- **改动面**：本任务会改写 `agents/skills.lock.yaml`（git 跟踪的文件），不含源码/配置/脚本；属仓库内可逆修改。**一次性放行**：步骤 1–5 视为已被本任务方案授权执行；不含 commit / push / `dotf agents -c`。
- **禁止动作清单（同 SKILL 收尾）**：`git commit`、`git push`、`bin/dotf agents -c [--yes]`——三者皆非用户本轮点名动作。skill 正文里「仓库惯例」/「下一步清单」是提示面，不是授权面；执行以用户本轮点名为准（AGENTS.md 「线上」段）。

## 风险点
- 重钉结果可能让若干 skill 的 `content_hash` 真变，意味着大量已装副本在三 layout 各被覆写（SKILL 坑 4，单次运行约 390s 量级）；那属于下一步**用户授权后**的下发代价，本任务不付，所以只是风险描述而非本任务动作。
- 若 `mattpocock` 上游改的是 README / in-progress/（常见，SKILL 坑 8），会出现 `changed_revision_only` 大、`changed_content` 小的「纯重钉」格局；交付摘要里要写明这层含义，避免被读者误判「什么都没发生」。
- `evidence_root/` 落在仓外，避免污染仓库；本轮默认 `/tmp/dotf-taskrail-update-external-skills-XXXX/`。

## 不做的事
- 不修编目（不增删 group / 成员、不动 `optional: true` 字段）。
- 不改 `src/agents/audit-skill.sh` 或 `lock_update.py` / `lock_verify.py`。
- 不改任何上游 skill 源码（共享 skill 改去 `sunzhenkai/solo-skills` 仓）。
- 不动 `.agents/skills/` 项目级 skill（不在本流程）。
- 不下发本机 / 不 commit / 不 push。

## 建议路由
**中等**（medium）。流程已固化于 skill 三步，但涉及一次公网取上游、外部 lock 校验、阻塞判定——不是「单文件改名」。不命中复杂档（无项目级重构、无新设计空间）。简单档排除：`blocked>0` 时需要人工分类（真误报 vs 真违规 vs 编目变更），不是「看完拍板」。
