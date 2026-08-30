# 结果

- status: applied
- applied_at: 2026-08-30 12:10 (UTC+8)

## 实际改动

| 文件 | 变化 |
|------|------|
| `SKILL.md` | 非目标中三方/外来仓 5 行压成 2 行并指向 routing.md；build 第 7 步拆成 7/8/9，原 8～10 顺延为 10～12 |
| `references/routing.md` | 新增「输入边界」小节，纳入 `symbols`，列出 vendor / node_modules / 虚拟环境 / submodule / 嵌套仓 / replace / Composer path |

build 从 10 步变为 12 步，每步一件事；`complete` 必建 notes 的结论写进该条自身标题，
不再用「见下一步」做编号交叉引用。

## 验证

- `git apply --check --recount`：routing.md hunk 初次手写上下文匹配失败，改用 `difflib` 从文件真实内容生成后通过
- `git apply --recount`：通过
- `git diff --check`：无空白错误
- `python3 -m unittest discover`：50 tests OK（依赖措辞「深入行为承载符号」「测试只写覆盖意图」「简述」「外来仓」「复杂业务逻辑」「线性三步」均保留）

## 偏差

`change.patch` 的 routing.md 部分由脚本重新生成，SKILL.md 部分为手写且一次通过。
生成脚本写在 `/tmp` 并已删除，未进入仓库；修正期间未编辑任何生产文件。

## 经验

手写含大量全角标点的中文长行 hunk 容易出现肉眼不可见的匹配失败。
后续 patch 的长行改动优先用 `difflib` 从真实文件内容生成，而不是手抄上下文。
