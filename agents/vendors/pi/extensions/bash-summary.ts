// 为内置 bash 工具补充结构化 description 参数，由模型调用时直接提供语义摘要，供 compact-output 折叠态展示。
// 执行仍完全委派给原生 createBashToolDefinition（保留 ctx.cwd 动态目录、输出截断与结构化返回值）。
// 下发位置：~/.pi/agent/extensions/bash-summary.ts（dotf pi -c）
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { createBashToolDefinition } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

const bashWithDescriptionSchema = Type.Object({
  description: Type.String({
    description:
      "Brief human-readable summary of what this command does (2-10 words, e.g. '检查 git 状态' or '更新外部 skills 锁文件'). Shown directly in collapsed tool output.",
  }),
  command: Type.String({ description: "Shell command to execute" }),
  timeout: Type.Optional(
    Type.Number({ description: "Timeout in seconds (optional, no default timeout)" }),
  ),
});

export default function (pi: ExtensionAPI) {
  const baseBash = createBashToolDefinition(process.cwd());
  pi.registerTool({
    ...baseBash,
    name: "bash",
    parameters: bashWithDescriptionSchema,
    async execute(toolCallId, params, signal, onUpdate, ctx) {
      return baseBash.execute(
        toolCallId,
        { command: params.command, timeout: params.timeout },
        signal,
        onUpdate,
        ctx,
      );
    },
  });
}
