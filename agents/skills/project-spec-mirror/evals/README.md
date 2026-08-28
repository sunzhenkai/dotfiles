# Evals

本 Skill 的可验证成功标准。任务完成前对照 `cases.yaml` 检查关键输出与约束。详尽不等于每源文件一页；相关 case 见 `detailed-deepens-pages-not-files-tree` 等。

## 怎么跑

1. 选出与当前任务相关的 cases（`kind` + 描述匹配）
2. `judge: deterministic`：按 `expect.must` / `expect.must_not` 逐条核对，只报 pass/fail
3. `judge: llm`：仅当无法确定性判断时使用；给出简短判定与依据，不编分数
4. 任一条失败 → 先修输出再交卷，不要带着 fail 声称完成

新增 case 必须能从 Skill 原文或真实回归事故找到依据。禁止虚构。
