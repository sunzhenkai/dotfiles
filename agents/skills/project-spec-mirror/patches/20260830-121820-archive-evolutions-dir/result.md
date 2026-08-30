# 结果

- status: applied
- applied_at: 2026-08-30 12:19 (UTC+8)

## 实际改动

新增 `evolutions/README.md`（16 行）：标注该目录为历史归档、`*.candidate` 非现行版本、
现行协议是 `patches/`、`experience/` 是输入而 `patches/` 是输出。

## 验证

- `git apply --check --recount` / `git apply --recount`：通过
- `git diff --check`：无空白错误
- `python3 -m unittest discover`：50 tests OK
- 历史文件未被改动：patch 只新增一个文件

## 偏差

无。
