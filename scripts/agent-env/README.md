# Compatibility / internal layer for agent-env

本目录实现 MCP sync 与检查逻辑（`sync.py`、`doctor_impl.py`、`common.py`）。

**请优先使用统一入口：**

```shell
dotf -c agents
dotf -c agents --doctor
scripts/agents/sync.sh all
python3 scripts/agents/doctor.py
```

兼容包装：

| 文件 | 行为 |
|------|------|
| `sync.sh` | 委托 `scripts/agents/sync.sh --env-only` |
| `doctor.py` | 委托 `scripts/agents/doctor.py` |

不要长期直接依赖本目录脚本作为用户入口，以免双路径漂移。
