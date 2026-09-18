# 模型清单格式

私有文件 `<data_root>/agents/models.yaml`，不进本仓库。按 Agent Kind 列出使用者实际会用的模型 id。

```yaml
cursor:
  - grok-4.6
codex:
  - gpt-5.2
```

`list_assignments.py` 把它与画像里的默认模型合并。清单没有的 id 仍允许在 Decision Surface 手打。
