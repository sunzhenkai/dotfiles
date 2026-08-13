# 核心约束

`role-based-reviewer` 的共享约束、命令边界、角色协作与结尾巴块。

## 核心约束

- **只读**：不修改业务代码、不创建分支、不提交、不写文档/规格；用户明确要求修复时再改
- **先过门禁**：未过 SKILL.md 三道门禁不得预加载、不得分角色审查
- **结论绑定路径**：findings MUST 绑定 `path:line` 或符号/调用关系，禁止悬空断言
- **不确定就标出来**：不编造问题凑数；没有问题就明说没有
- **不越界**：不审查目标范围外的文件，除非它是理解目标所必需的上下文
- **用户要求实现/固化/提案时**：只给角色化上下文与下一步建议，引导到现有执行 skill（见下表），本 skill 不代做

## 命令边界

| | engineer | algo | data | sre | ops | biz | product | design | qa |
|---|---|---|---|---|---|---|---|---|---|
| 视角 | 在线实现、性能、调用链 | 模型/策略/实验 | 管道、数仓、口径 | 集群、监控、发布 | 业务配置、灰度、运营流程 | 对外对接、多租户 | 需求与 spec | 视觉与交互 | 可测性与回归 |
| 典型下游 | `task-design`、`task-workflow`、`service-manager` | `task-design`、`task-workflow` | `task-design`、`task-workflow` | `service-manager`、部署/CI 相关约定 | 运营手册 / 配置变更流程 | 协议/对接文档 | `task-design`、`task-workflow`、OpenSpec（若项目有） | `dotf-ui-design`（仅用户点名时） | 测试与回归计划 |
| 运行态上下文 | 按需 | 否 | 否 | 按需 | 按需 | 否 | 否 | 否 | 否 |
| 输出 | RoleBrief / 审查报告 | 同左 | 同左 | 同左 | 同左 | 同左 | 同左 | 同左 | 同左 |

本 skill **不调用**其他 skill 的内部逻辑；在输出里写清「下一步建议执行哪个 skill」，由用户/主 agent 触发。项目里没有对应 skill 时，写清动作本身，不要编造不存在的 skill 名。

## 多角色协作

- `roles` 可指定 1 个或多个；未指定时默认 **engineer**，其它角色须强信号或用户确认（门 2）
- 每个角色保留独立证据与 findings，不得合并成无归属结论
- 共享对象按下方 redirect 与 [role-vocabulary](role-vocabulary.md) 的主问题归属定主责，其余为协作
- 下一步默认只选主责角色的一个动作；并行时拆任务并注明依赖
- 不为「让每个角色都有输出」而发明 findings（门 3）

## 角色间 redirect

命中边界时换视角，不要越权下结论：

| 边界 | 共享对象 | 判据 | redirect |
|------|---------|------|---------|
| sre ↔ ops | 灰度、配置 | 基础设施（集群/部署/配置下发/告警）→ sre；业务侧（功能开关/运营规则/渠道配置）→ ops | 互引 |
| sre ↔ engineer | 重启 / OOM / 稳定性 | 集群·部署·调度·探针 → sre；代码缺陷·GC·调用链 → engineer | 互引 |
| engineer ↔ algo | 推理 / 排序服务 | 可用性·性能·发版 → engineer；模型效果·策略·实验 → algo | 互引 |
| algo ↔ data | 特征 / 样本 / 模型分发 | 在线推理与效果 → algo；离线管道·样本质量·数仓分层 → data | 互引 |
| engineer ↔ data | 事件 / 追踪管道 | 在线可用性 → engineer；数据流与口径 → data | 互引 |
| ops ↔ engineer | 服务内业务开关、规则 | 配置/灰度/运营异常 → ops；代码缺陷 → engineer | 互引 |
| biz ↔ product | 需求 / spec | 消费 spec 做对接 → biz；产出 spec 做提案 → product | 互引 |
| biz ↔ engineer | 外部协议 vs 内部实现 | 合作方/多租户对接 → biz；内部服务实现 → engineer | 互引 |
| design ↔ product | 体验 | 视觉/交互/无障碍 → design；价值/范围/文案 → product | 互引 |
| design ↔ engineer | UI 落地 | 视觉与交互规格 → design；实现与性能 → engineer | 互引 |
| qa ↔ engineer | 测试 | 覆盖/回归/可测性 → qa；实现正确性 → engineer | 互引 |

## 结尾巴块

所有输出 MUST 在全文末尾追加 `### 总结与置信度`：

| 置信度 | 判据 |
|--------|------|
| 高 | 结论全部绑定明确路径，无 unknowns |
| 中 | 含 1–2 项 unknowns 或待验证项，主体已锚定 |
| 低 | 上下文不足，主要靠推断；建议缩小范围或补充材料 |

末尾 MUST 给出「下一步」（主责动作 / 是否需要运行态上下文 / 是否跨角色 redirect）。
