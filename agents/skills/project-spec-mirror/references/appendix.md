# 附录（默认不读）

仅当用户明确要求、或 `status.layout=legacy` 时使用。不要在普通 build 预加载本文件。

## 旧金字塔镜像

上一版 Skill 用顶层 `modules/` `facets/` `runtime/` `build/` `context/` 当阅读树。这不是通用工程约定。

若 `detect` / `status` 报 `layout=legacy`：

- 阶段按 `rebuild`（当 build），按现行 `briefing/` + `agent/` + `evidence/` 重写。
- 遗留目录停更、不删，除非用户要求删除。
- 不要继续加深旧模块文件表或 `notes/`。

## 改这个仓

要按切片改当前仓库、灰度或对照另一实现时，可自建 `facets/`（SOURCE / CONTRACT / SLICE / VERIFY / TRAFFIC）。契约链到已有 `agent/specs/`，不要复制一套行为叙述。

## 复原当前栈

要按现有 compose/工具链跑起来时，可自建 `evidence/realization/`：进程、端口、构建命令。这不是复现验收。密钥仍 `<REDACTED>`。
