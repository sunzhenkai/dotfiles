# 交卷前自检

只核对本轮涉及的组。不满足先修再回执。

## 每轮

- 密钥值 `<REDACTED>`（`AppKey` / `SecretKey` / token / password）。
- 没有自动 commit / push；只写 `status` 给出的 `spec_root`；没碰目标仓 `openspec/`。
- 退出码 2 等用户；收尾只走 `$SPECCTL finalize`。
- `mode` 是 `briefing` 或 `reconstructable`；能力状态只有 `draft` | `ready`。

## 双读者

- 人读 `briefing/`，无「完整逻辑」/ full logic、无「## 文件」/ `## Files` 表、无清单文件版本行。
- Agent 读 `agent/specs/`，格式 Purpose / Requirement / Scenario。
- 没有默认生成 `facets/` 或 `evidence/realization/`。

## 门禁

- `finalize` 已成功。若 `layout=legacy`，按 [appendix.md](appendix.md) rebuild，不要在旧文件表上 update。
- `reconstructable`：未映射代码入口已进 source-map 或「未指定」；无幽灵 map 行。
- update 的 `unmapped` 已消化。
- **复现抽检（reconstructable）：** 只读 `agent/`（不打开源码与 evidence），口述 1 条主 Scenario 的 WHEN/THEN。答不出不得称完成。

## 图与回执

- 复杂业务逻辑有 archify HTML 并链回 `briefing/flows/`；不能只留 JSON 或假 HTML。
- 回执含项目、`spec_root`、粒度、分支/commit、本轮阶段、变更层。
