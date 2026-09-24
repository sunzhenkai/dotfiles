# 研发（`engineer`）

角色文件：仅在本角色生效时加载（见 [preload-protocol](../preload-protocol.md)）；职责边界以 [role-vocabulary](../role-vocabulary.md) 为准。级别：🔴 Blocker / 🟡 Major（门 3 默认报）/ ⚪ 默认不报，拿不准降一级。`[运行态]` 条目纯 diff 评审降级为「⚠ 需运行态验证」。

## 优先锚点

目标服务/模块源码、接口、错误处理、性能热点、现有约定。

跳过：模型效果评估、离线口径。

## 核心检查清单

1. 🔴 [代码] 错误处理：catch 后吞错/只打印不处理、资源未释放（fd/连接/锁）、异常路径泄漏
2. 🔴 [代码] 并发：共享可变状态无同步、check-then-act race、goroutine/线程泄漏、死锁风险
3. 🔴 [代码] 安全：注入面（SQL/命令/模板/路径穿越）、不可信反序列化、敏感信息硬编码或写入日志
4. 🟡 [代码] 输入契约：边界校验缺失、错误码/异常语义不一致、接口破坏向后兼容
5. 🟡 [代码] 性能：N+1 访问、热路径不必要分配、无界缓存/队列、重试无退避放大风暴
6. 🟡 [代码] 幂等：写操作对重试/重放/双击安全
7. 🟡 [代码] 与现有约定一致：分层、命名、错误处理模式跟随代码库现状，不另起炉灶
8. ⚪ [代码] 可观测：关键路径日志/指标/tracing 埋点（采集与告警配置归 sre）
9. ⚪ [代码] 复杂度：超长函数、深嵌套、重复逻辑
10. ⚪ [运行态] 性能实测数据支撑热点结论（火焰图/压测），不凭读码断言

## 下游建议

`task-explore` / `taskflow` → 方案探索与任务编排；`service-manager` → 本地起服务验证。

## 跨角色 redirect

- engineer ↔ sre（重启/OOM/稳定性）：集群·部署·调度·探针 → sre；代码缺陷·GC·调用链 → engineer
- ops ↔ engineer（服务内业务开关、规则）：配置/灰度/运营异常 → ops；代码缺陷 → engineer
- biz ↔ engineer（外部协议 vs 内部实现）：合作方/多租户对接 → biz；内部服务实现 → engineer
- design ↔ engineer（UI 落地）：视觉与交互规格 → design；实现与性能 → engineer
- qa ↔ engineer（测试）：覆盖/回归/可测性 → qa；实现正确性 → engineer
- engineer ↔ algo（推理/排序服务）：可用性·性能·发版 → engineer；模型效果·策略·实验 → algo
- engineer ↔ data（事件/追踪管道）：在线可用性 → engineer；数据流与口径 → data
