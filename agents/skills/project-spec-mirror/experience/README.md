# Experience

供 Skill 维护者记录真实执行中的失败、成功与可复用规律。不要记录 trivial information。

普通 project spec 镜像任务不得自动写入本目录；只有用户明确要求维护或演进本 Skill 时，才由当前仓库约定的维护流程创建记录和生产变更。

```text
failures/  → 失败案例
successes/ → 成功案例
patterns/  → 从多个案例中提炼出的可复用规律
```

## 何时写入

- 失败、用户纠正、明显成功
- 新的有效执行方法
- 可复用的经验

## 何时不写入

- 一次性环境问题（网络闪断、用户打错字）
- 与 Skill 无关的闲聊
- 尚未发生的「预期失败」

## 条目格式

`experience/<bucket>/<YYYYMMDD>-<slug>.md`

必填：Date / Kind（failure | success | pattern）/ Skill / Context / What happened / Lesson。

一次性特例在 Lesson 写明 `Experience only`，不要建议改 Skill。

`patterns/` 至少要有 **两次以上** 同类 evidence 才建立。单次失败只进 `failures/`。

空的 `failures/` `successes/` `patterns/` 各放一个 `.gitkeep`。
