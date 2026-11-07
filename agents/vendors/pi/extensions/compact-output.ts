// 内置工具行的紧凑显示：成功只留一行摘要，失败给末 3 行，展开时看全文。
// 只替换 renderResult，renderCall 和执行逻辑沿用 pi 原生实现。
// 下发位置：~/.pi/agent/extensions/compact-output.ts（dotf pi -c）
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Text } from "@earendil-works/pi-tui";

// grep/find/ls 是内置名，ffgrep/fffind/fff-multi-grep 是 pi-fff 的替代名：
// 内置搜索工具默认不在 defaultTools 里，实际会话走 fff，两套都要覆盖。
const LIST_TOOLS: Record<string, { unit: string; emptyLabel: string; emptyText: string }> = {
  grep: { unit: "行", emptyLabel: "无匹配", emptyText: "No matches found" },
  ffgrep: { unit: "行", emptyLabel: "无匹配", emptyText: "No matches found" },
  "fff-multi-grep": { unit: "行", emptyLabel: "无匹配", emptyText: "No matches found" },
  find: { unit: "个", emptyLabel: "无匹配", emptyText: "No files found matching pattern" },
  fffind: { unit: "个", emptyLabel: "无匹配", emptyText: "No files found matching pattern" },
  ls: { unit: "项", emptyLabel: "空目录", emptyText: "(empty directory)" },
};
const SUMMARY_TOOLS = new Set(["bash", ...Object.keys(LIST_TOOLS)]);
const FAILURE_TAIL_LINES = 3;
const SLOW_MS = 1000;
const BASH_TRAILER =
  /\n\n(?:Command exited with code (\d+)|Command aborted|Command timed out after [\s\S]*|Command terminated without an exit code)$/;
const BASH_EXIT_CODE = /\n\nCommand exited with code (\d+)$/;
const BASH_TRUNCATION = /\n\n\[Showing (?:last|lines) [\s\S]*\]$/;
const LIST_NOTICE = /\n\n\[[\s\S]*\]$/;
const ANSI_PATTERN = /\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b\[[0-9;?]*[ -/]*[@-~]/g;

interface Theme {
  fg(token: string, value: string): string;
}

interface ToolResult {
  content?: Array<{ type?: string; text?: string }>;
  details?: {
    truncation?: { truncated?: boolean };
    fullOutputPath?: string;
    matchLimitReached?: number;
    resultLimitReached?: number;
    entryLimitReached?: number;
    linesTruncated?: boolean;
  };
}

interface RenderOptions {
  expanded?: boolean;
  isPartial?: boolean;
}

interface RenderContext {
  durationMs?: number;
  isError?: boolean;
}

interface Summary {
  ok: boolean;
  headline: string;
  body: string;
  notice?: string;
}

function textOf(result: ToolResult): string {
  return (result.content ?? [])
    .filter((block) => block.type === "text")
    .map((block) => block.text ?? "")
    .join("\n")
    .replace(ANSI_PATTERN, "")
    .replace(/\r/g, "");
}

function lineCount(text: string): number {
  return text ? text.split("\n").filter((line) => line.trim() !== "").length : 0;
}

function lastLines(text: string, count: number): string {
  const lines = text.split("\n").filter((line) => line.trim() !== "");
  return lines.slice(-count).join("\n");
}

function durationSuffix(context: RenderContext): string {
  const ms = context.durationMs;
  if (typeof ms !== "number" || ms < SLOW_MS) return "";
  return ` · ${(ms / 1000).toFixed(1)}s`;
}

function summarizeBash(result: ToolResult, raw: string, isError: boolean): Summary {
  const exitMatch = BASH_EXIT_CODE.exec(raw);
  const exitCode = exitMatch ? Number(exitMatch[1]) : undefined;
  const body = raw.replace(BASH_TRAILER, "").replace(BASH_TRUNCATION, "").trim();
  const ok = !isError && (exitCode === undefined || exitCode === 0);
  const failedExit = exitCode === undefined ? "失败" : `exit ${exitCode}`;
  const fullPath = result.details?.fullOutputPath;
  return {
    ok,
    headline: ok ? (body ? `${lineCount(body)} 行` : "无输出") : failedExit,
    body,
    notice: fullPath ? `全文: ${fullPath}` : undefined,
  };
}

function summarizeList(tool: string, result: ToolResult, raw: string, isError: boolean): Summary {
  const body = raw.replace(LIST_NOTICE, "").trim();
  if (isError) {
    const message = body.split("\n").find((line) => line.trim() !== "") ?? "失败";
    return { ok: false, headline: message, body };
  }
  const details = result.details;
  const notices: string[] = [];
  if (details?.matchLimitReached) notices.push(`命中上限 ${details.matchLimitReached}`);
  if (details?.resultLimitReached) notices.push(`结果上限 ${details.resultLimitReached}`);
  if (details?.entryLimitReached) notices.push(`条目上限 ${details.entryLimitReached}`);
  if (details?.truncation?.truncated) notices.push("输出已截断");
  if (details?.linesTruncated) notices.push("长行已截断");

  const empty = body === LIST_TOOLS[tool].emptyText;
  const spec = LIST_TOOLS[tool];
  const headline = empty ? spec.emptyLabel : `${lineCount(body)} ${spec.unit}`;
  return {
    ok: true,
    headline,
    body: empty ? "" : body,
    notice: notices.length > 0 ? notices.join(" · ") : undefined,
  };
}

function summarize(tool: string, result: ToolResult, isError: boolean): Summary {
  const raw = textOf(result).trim();
  return tool === "bash" ? summarizeBash(result, raw, isError) : summarizeList(tool, result, raw, isError);
}

function renderSummary(
  tool: string,
  result: ToolResult,
  options: RenderOptions,
  theme: Theme,
  context: RenderContext,
): Text {
  if (options.isPartial) {
    return new Text(theme.fg("muted", "… 运行中"), 0, 0);
  }

  const summary = summarize(tool, result, context.isError === true);
  const duration = durationSuffix(context);
  const head = summary.ok
    ? theme.fg("success", `✓ ${summary.headline}${duration}`)
    : theme.fg("error", `✗ ${summary.headline}${duration}`);
  const lines = [head];

  if (options.expanded) {
    if (summary.body) lines.push(theme.fg("toolOutput", summary.body));
  } else if (!summary.ok) {
    const tail = lastLines(summary.body, FAILURE_TAIL_LINES);
    if (tail) lines.push(theme.fg("toolOutput", tail));
  }
  if (summary.notice) lines.push(theme.fg("muted", summary.notice));

  return new Text(lines.join("\n"), 0, 0);
}

export default function (pi: ExtensionAPI) {
  pi.registerToolRenderer((toolName, next) => {
    if (!SUMMARY_TOOLS.has(toolName)) return next();
    return {
      ...(next() ?? {}),
      renderResult(result, options, theme, context) {
        return renderSummary(toolName, result as ToolResult, options, theme, context);
      },
    };
  });
}
