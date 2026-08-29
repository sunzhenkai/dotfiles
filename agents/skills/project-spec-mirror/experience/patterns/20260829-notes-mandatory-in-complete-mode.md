# detail_level=complete 下必须建 modules/notes/

- Date: 2026-08-29
- Kind: pattern
- Skill: project-spec-mirror
- Status: 候选 → 晋升后成为正式规则

## Evidence

- `experience/failures/20260829-notes-missed-in-complete-mode.md`（task 1.11 feature-extraction-lib 漏 6 个 notes/）
- task 1.10（algogear-bidder/external，detail=complete）已建 6 个 notes/ 主题：ali_express DPA URL 清洗 / lazada 接口偏离根因 / shein ID 大写 / tiktok 双层 HMAC / rta DialOption / config 注入矩阵

## Pattern

`detail_level=complete` 模式下，模块 README 已写完每个文件核心方法，剩余"读源码看不出来"的内容（跨文件契约、异常边界、race 分析、监控盲区、框架宏约束）必须落到 `modules/<m>/notes/`，而不是塞进模块 README。

触发条件（满足任一即建 1 篇 notes/，整体 ≥5 篇、覆盖 ≥3 类）：

1. 跨文件契约（builder 配对 / init→extract 时序 / 依赖注入矩阵 / shared l0_rfm 共享）
2. 一致性失败路径与正常路径不同（parse 失败 ≠ throw / L1 抛 vs L0/L2 不抛 / silent corruption）
3. 并发/锁的 race 分析（shared_mutex double-check / is_done_ 标记 / lock_guard+double-check）
4. 监控盲区（声明了 bvar 但未 <<1 / FE_ERROR 无对应 counter / AddCounter 接错 msg 维度）
5. 框架/预处理器的使用约束（BOOST_PP_SEQ_FOR_EACH 宏展开顺序 / 字段名规范 / ABI 兼容性 / --ff-only 而非默认 pull）

notes/ 的**命名**是 topic（易踩坑的概念）而非源相对路径；与已有 `notes/<source-rel>.md` 命名并列。

## Action

- modes.md 改档位分支（complete 必建 / important opt-in / concise+lightweight 不建）
- SKILL.md build 步骤新增 8.5 + build 前 grep 同 group 已镜像 notes/ 做参考
- evals/cases.yaml 新增 complete-mode-notes-mandatory case

## Reusable for

后续 245 个 mirror task（mirror-repos-from-list change）；任何 detail=complete 的初次 build 或 update 后新增 hot path。
