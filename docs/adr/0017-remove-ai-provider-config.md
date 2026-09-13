# 移除 AI provider 及密钥声明

推翻 ADR-0016「保留 codex/opencode/pi provider 与密钥声明」的决策：当时的判断是五家 provider（MiniMax / Kimi / 智谱 / SCNet / DeepSeek）声明维护成本低、可复现性好。实际运行后，provider 端点、模型名、catalog 元数据（reasoning level / 模态 / truncation）快速漂移，仓库需要持续跟进各家网关的协议细节（Responses vs Chat、国内/海外站、额度策略），维护成本明显高于收益；且把密钥检查固化在 env schema / acceptance / doctor 中，等于把「本机私有选择」做成了仓库级契约。

决定：整体移除。`agents/vendors/codex/config.toml` 删除 `model*` 与全部 `[model_providers.*]`，删除 `model-catalogs/` 五个 catalog 及 codex producer 的 catalog 硬校验；`agents/vendors/opencode/opencode.json` 删除 `provider` 段与 `model` 字段，`opencode_merge()` 退化为通用 vendor→目标 merge；`agents/vendors/pi/settings.json` 删除 `defaultProvider` / `defaultModel` / `enabledModels`，删除 `auth.json.example` 与 `_pi` producer（pi 配置策略相应改为 copy）；`config/editors/zed/settings.json` 删除 zhipu 段。

随之移除的还有：OCR 模块（`scripts/modules/ocr/`、`config/tools/ocr/`，其 api_key 走环境变量回退）、dsh 模块（`scripts/modules/dsh/`）、archived 的 shell_gpt 配置（`config/tools/shell_gpt/`）；`agents/env/env.schema.yaml` 清空为 `variables: {}`（profiles / doctor 的 env 检查自然 no-op）；acceptance 与 CI 的 AI key unset / 断言随之精简。

保留：通用设施不动——`codex_expand_env()`、base+local 合并、`config_deploy` 的 manifest / 安全写、`.example` 源展开机制、`_private_overlay`、logseq producer、`src/dotf_core/sanitize.py` 与 `agents/env/security.yaml` 扫描规则（L6 描述改为通用「外部 API 调用」措辞）、`scripts/modules/senv/`。各 vendor 的工具使用说明与 projects 本地化机制继续生效；provider / 模型 / 密钥完全由本机 overlay（如 `codex.local_toml`）或各工具登录流程自管。

备选：只删 catalog 保留 provider 声明——provider 表本身仍是主要漂移源，否决；把 provider 声明移到 gitignored 本机文件——与 XDG overlay 机制重复，直接用 overlay 即可，不另起一套。

后果：`dotf` 不再安装任何 LLM 配置，已部署机器上的 `~/.codex/model-catalogs/` 等旧文件不做自动清理；`-f` / `--*-profile` 切换 provider 的入口本就不存在，语义不变。若未来要恢复 provider 声明，git 历史与 ADR-0016 描述的耦合面是重新评估的起点。
