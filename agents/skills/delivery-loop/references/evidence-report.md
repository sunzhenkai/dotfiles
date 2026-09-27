# Evidence and Report

## Evidence root

`<slug>` 从目标归纳为 kebab-case；冲突时追加运行时间戳或 run id。优先使用项目已有临时目录约定；没有约定时使用：

```text
/tmp/delivery-loop/<slug>
```

证据路径一律写绝对路径。不把运行截图、导出日志或数据库写进共享 skill。

## Manifest

每次运行写 `manifest.md`：

```markdown
# Delivery Loop Manifest

- goal:
- mode:
- started_at:
- code_state:
- evidence_root:
- slices:
  - name:
    entry:
    action:
    exit:
    tests:
    runtime_evidence:
- role_review:
- triage:
- repair_round:
- rubric_source: taskflow skill: references/acceptance-rubric.md
- benchmark_profile_hash: <仅 benchmark；不写给实现者>
- final_scores:
- pending_degradations:
- stopped_reason:
```

## Required evidence

- 启动命令与输出
- 自动化测试命令、退出码、摘要
- 每个核心闭环的截图或导出日志
- 失败路径 / 空态 / 错误态证据（如任务有 UI）
- 修复前后对照
- role review 原文或路径
- patch 校验与应用记录（如有 skill gap）
- 最终数据库 / 进程状态（如涉及服务）

## Completion gates

### normal

- taskflow checkbox 全勾
- 完成判据成立
- 质量画像字段完整
- pending 降级为 0
- confirmed 降级可追踪
- 评分维度、UI/UX 子项与通过线全部按 `rubric_source` 指向的 taskflow acceptance rubric 判定，不另设数字口径
- 测试与运行证据齐
- 启动说明、已知限制、后续动作齐

### benchmark

- 实现者输入隔离可审计
- 首次盲测已记录目标原文、运行约束与评审专用画像哈希；若是回归复跑，三者与基线一致
- failure 已逐条归因
- skill gap 有可审计 patch
- patch 后受影响切片复验通过
- 全链路评分达到 `rubric_source` 指向的 normal 通过线
- 输出 skill 改进效果，不宣称隐藏期望已告知实现者

## Final report

一页内输出：

1. 结论：完成 / 有条件完成 / 停止
2. 交付物路径
3. 启动与测试命令
4. 五维分数与 UI/UX 六子项
5. 证据路径
6. 降级确认状态
7. 失败归因与修复
8. 剩余限制
9. 下一步

停止时不得省略未完成项；部分通过不是完成。
