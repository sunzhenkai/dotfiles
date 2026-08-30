# 拆开密集的 build 步骤，把边界细则下沉到 routing.md

- skill: project-spec-mirror
- risk: medium
- 依据: skill-creator「progressive disclosure：SKILL.md 做路由与判定，细则进 reference」

## 问题

1. build 第 7 步一条编号里塞了五件互不相干的事：模块两表必备、`detail_level` 三档定义、
   回应「每个文件一页」、遗留 `files/` 处置、跨仓主题参考。一条编号里放五件事，
   执行时容易只做到前两件就往下走——历史上已经出现过 `fix-build-step-number` 这类补丁。
2. 「非目标」里混进了 `vendor/`、`node_modules/`、submodule、`replace` / Composer path
   这些操作细则，而同一批边界在 `routing.md` 和 `layout.md` 各写了一遍，三处措辞已经开始漂移。
   `symbols` 只在 SKILL.md 那一份里被点名共用边界，routing.md 那份漏了它。

## 改动

1. SKILL.md build 第 7 步拆成三条：
   - 7：模块 README 两表必备，并说明为什么（update 的路由靠这两个标题解析）；
   - 8：`detail_level` 三档如何覆盖文件表，细则指向 `modes.md`；
   - 9：如何回应「每个文件一页」与无范围的热点请求、遗留 `files/` 处置、跨仓主题参考。
   原第 8～10 步顺延为 10～12，`complete` 必建 notes 的结论改为在本条标题内自述，
   不再用「见下一步」做编号交叉引用（编号一变就失效）。
2. SKILL.md「非目标」中三方与外来仓的 5 行（含 3 个子条）压缩为 2 行，明细指向 `routing.md`。
3. `references/routing.md` 补齐被下沉的明细：把 `symbols` 纳入同一条输入边界，
   列出 `vendor/` / `node_modules/` / 虚拟环境 / submodule / 嵌套仓 / `replace` / Composer path，
   并写明不为它们建模块、文件表行、`notes/`、概念或切片。

## 非目标

- 不改任何行为语义：三档定义、notes 触发条件、遗留 `files/` 处置结论都保持不变。
- 不动 build 收尾那条（`coverage` → `validate` → `set-sync` → `validate`），
  它由后续的 `specctl finalize` patch 单独处理。
- 不改 `layout.md`：它那份是目录树语境下的一句话概括，保留无害。

## 验证

- `git apply --check --recount`
- `python3 -m unittest discover -s <skill-dir>/tests`（断言依赖的措辞：深入行为承载符号 / 测试只写覆盖意图 / 简述 / 外来仓 / 复杂业务逻辑 / 线性三步 均需保留）
- 人工核对 build 步骤编号连续、无「见下一步」式交叉引用
