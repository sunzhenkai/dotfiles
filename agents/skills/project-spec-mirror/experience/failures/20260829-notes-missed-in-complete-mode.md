# complete 模式下漏掉 modules/notes/ 详注

- Date: 2026-08-29
- Kind: failure
- Skill: project-spec-mirror
- Context: detailed / detail_level=complete 给 algogear-bidder/feature-extraction-lib 跑 mirror，按 SKILL.md build 步骤写金字塔 + 切面 + 概念/实体/流/模块页

## What happened

按 SKILL.md 的 build 步骤完成 5 投影 INDEX + facets × 5 + concepts × 5 + entities × 6 + flows × 3 + modules × 12 + 4 张 archify 图；validate 通过；set-sync 锁定 commit 9d239e9。用户 review 后明确指出："怎么没整理 nodes 文件？"

复盘：

- `detail_level=complete` 要求"完整整理所有源文件、不得遗漏"——但模块 README 已经把每个文件的核心方法完整逻辑写完，再补什么？
- modes.md line 52 说 `notes/` 默认不建，只对"用户点名或符合热点条件的路径"建——但没给"热点条件"的可执行判据
- 已知 `algogear-bidder/external` mirror（更早 task）建了 6 个 notes/——但本次 build 时没扫已镜像仓的 `modules/*/notes/` 做对照
- 真正应该进 notes/ 的内容（"读源码看不出来"的隐性契约）：OptionsBuilder 的 `THROW_ON_EMPTY_OPTIONAL` 抛错契约、L1 抛 vs L0/L2 不抛的异常边界、shared_mutex double-check 的 race 分析、ruf/duf 4 层解析失败的 silent corruption 风险、WipeSize Apple 设备 hack、BOOST_PP 扩展规则的 4 步流程

## Lesson

- `detail_level=complete` 模式下 `notes/` 是**必建**，不是 opt-in："完整覆盖"含"显式写跨文件契约与易踩坑的设计选择"
- 至少 5–8 个 notes/，按"跨文件契约 / 异常边界 / race 分析 / 解析容错 / 框架机制"5 类组织
- 触发条件（满足任一即建）：
  1. 跨 ≥2 个文件的契约（builder 配对、init→extract 时序、依赖注入矩阵）
  2. 一致性 fail 路径与正常路径不同（parse 失败 ≠ throw、L1 抽 vs L0/L2 不抛）
  3. 并发/锁的 race 分析（shared_mutex double-check、is_done_ 标记）
  4. 监控盲区（声明了 bvar 但未 <<1、FE_ERROR 无对应 counter）
  5. 框架/预处理器的使用约束（宏展开顺序、字段名规范、ABI 兼容性）
- build 流程应在 modules README 之后加一步："列出跨文件契约 → 写 5–8 个 notes/"，不与已建模块冲突
- 复用对照：build 前先 grep `spec/<group>/<已镜像仓>/modules/*/notes/` 看同 group 内已有 mirror 的 notes/ 主题

## Reusable for

- 后续 245 个 mirror task（mirror-repos-from-list change）
- 所有 detail=complete 的初次 build 与 update 后新增 hot path

## Action

- 已就地补 6 个 notes/：options-builder-sequencing / l1-throws-vs-l0l2-no-throw / demand-cache-double-check / ruf-parse-resilience / md5-cluster-id-gen / preprocessor-feature-macros
- 写 experience/patterns/ 提示"build 末尾 grep 已镜像 notes/ 主题列表"
- 启动 skill-evolver 提议：把 modes.md 的"opt-in"改成"complete 模式下必建"，加 eval case
