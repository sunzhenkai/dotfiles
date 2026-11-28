// 极简输出渲染：默认 quiet 模式彻底隐藏思考占位（setHiddenThinkingLabel("")）与成功工具行，
// 仅在工作指示器（setWorkingMessage）实时提示当前工具，失败时保留错误与末 3 行，展开（Ctrl+O）看完整详情。
// 只替换 renderResult / renderCall（并设 renderShell: "self"），不重注册工具、不影响模型上下文。
// 支持 /compact-output [quiet|compact|off|status] 运行时切换；用户问答工具直通原生渲染。
// 下发位置：~/.pi/agent/extensions/compact-output.ts（dotf pi -c）
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Container, Text } from "@earendil-works/pi-tui";

const LIST_TOOLS: Record<string, { unit: string; emptyLabel: string; emptyText: string }> = {
  grep: { unit: "行", emptyLabel: "无匹配", emptyText: "No matches found" },
  ffgrep: { unit: "行", emptyLabel: "无匹配", emptyText: "No matches found" },
  "fff-multi-grep": { unit: "行", emptyLabel: "无匹配", emptyText: "No matches found" },
  find: { unit: "个", emptyLabel: "无匹配", emptyText: "No files found matching pattern" },
  fffind: { unit: "个", emptyLabel: "无匹配", emptyText: "No files found matching pattern" },
  ls: { unit: "项", emptyLabel: "空目录", emptyText: "(empty directory)" },
};

const PASSTHROUGH_TOOLS = new Set(["ask_user_question", "askUserQuestion", "AskUserQuestion"]);
const FAILURE_TAIL_LINES = 3;
const MAX_LABEL_LEN = 72;
const MAX_INLINE_RESULT_LEN = 48;
const SLOW_MS = 1000;

const BASH_TRAILER =
  /\n\n(?:Command exited with code (\d+)|Command aborted|Command timed out after [\s\S]*|Command terminated without an exit code)$/;
const BASH_EXIT_CODE = /\n\nCommand exited with code (\d+)$/;
const BASH_TRUNCATION = /\n\n\[Showing (?:last|lines) [\s\S]*\]$/;
const LIST_NOTICE = /\n\n\[[\s\S]*\]$/;
const ANSI_PATTERN = /\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b\[[0-9;?]*[ -/]*[@-~]/g;

const KEY_ARG_NAMES = [
  "path",
  "file_path",
  "query",
  "url",
  "command",
  "name",
  "id",
  "pattern",
  "title",
] as const;

const EMPTY_COMPONENT = {
  render: () => [] as string[],
  invalidate() {},
};

type OutputMode = "quiet" | "compact" | "off";

let outputMode: OutputMode = "quiet";

interface UiContext {
  hasUI?: boolean;
  cwd?: string;
  ui?: {
    notify?: (msg: string, level?: string) => void;
    setHiddenThinkingLabel?: (label?: string) => void;
    setWorkingMessage?: (message?: string) => void;
  };
}

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
    diff?: string;
    patch?: string;
  };
}

interface RenderOptions {
  expanded?: boolean;
  isPartial?: boolean;
}

interface RenderContext {
  args?: Record<string, unknown>;
  cwd?: string;
  durationMs?: number;
  expanded?: boolean;
  isError?: boolean;
  state?: Record<string, unknown>;
}

interface Summary {
  ok: boolean;
  headline: string;
  body: string;
  notice?: string;
}

function stripAnsi(text: string): string {
  return text.replace(ANSI_PATTERN, "").replace(/\r/g, "");
}

function singleLine(text: string, maxLen = MAX_LABEL_LEN): string {
  const clean = stripAnsi(text).replace(/\s+/g, " ").trim();
  if (clean.length <= maxLen) return clean;
  return `${clean.slice(0, Math.max(1, maxLen - 1))}…`;
}

function shortPath(rawPath: unknown, cwd?: string): string {
  if (typeof rawPath !== "string" || !rawPath.trim()) return "";
  let value = rawPath.trim();
  if (cwd) {
    const normalizedCwd = cwd.endsWith("/") ? cwd : `${cwd}/`;
    if (value === cwd) return ".";
    if (value.startsWith(normalizedCwd)) {
      value = value.slice(normalizedCwd.length);
    }
  }
  const home = typeof process !== "undefined" ? process.env?.HOME : undefined;
  if (home) {
    const normalizedHome = home.endsWith("/") ? home : `${home}/`;
    if (value === home) return "~";
    if (value.startsWith(normalizedHome)) {
      value = `~/${value.slice(normalizedHome.length)}`;
    }
  }
  return singleLine(value);
}

function bashDescription(args: Record<string, unknown> | undefined): string {
  if (typeof args?.description !== "string") return "";
  return stripAnsi(args.description).replace(/\s+/g, " ").trim();
}

function formatBashCall(args: Record<string, unknown> | undefined): string {
  const desc = bashDescription(args);
  if (desc) return singleLine(`$ ${desc}`);
  const cmd = typeof args?.command === "string" ? stripAnsi(args.command).trim() : "";
  return cmd ? singleLine(`$ ${cmd}`) : "$ (empty)";
}

function firstArgValue(args: Record<string, unknown> | undefined, cwd?: string): string {
  if (!args) return "";
  for (const key of KEY_ARG_NAMES) {
    const val = args[key];
    if (typeof val === "string" && val.trim()) {
      return key === "path" || key === "file_path" ? shortPath(val, cwd) : singleLine(val, 40);
    }
  }
  return "";
}

function formatCallLabel(
  toolName: string,
  args: Record<string, unknown> | undefined,
  cwd?: string,
): string {
  const pathVal = shortPath(args?.path ?? args?.file_path, cwd);

  if (toolName === "read") {
    const offset = typeof args?.offset === "number" ? args.offset : undefined;
    const limit = typeof args?.limit === "number" ? args.limit : undefined;
    let range = "";
    if (offset !== undefined && limit !== undefined && limit > 0) {
      range = `:L${offset}-${offset + limit - 1}`;
    } else if (offset !== undefined) {
      range = `:L${offset}+`;
    }
    return singleLine(`Read ${pathVal || "(unknown)"}${range}`);
  }

  if (toolName === "edit") {
    return singleLine(`Edit ${pathVal || "(unknown)"}`);
  }

  if (toolName === "write") {
    return singleLine(`Write ${pathVal || "(unknown)"}`);
  }

  if (toolName === "bash") {
    return formatBashCall(args);
  }

  if (toolName === "grep" || toolName === "ffgrep" || toolName === "fff-multi-grep") {
    const pattern = typeof args?.pattern === "string" ? singleLine(args.pattern, 32) : "";
    const inPart = pathVal ? ` in ${pathVal}` : "";
    return singleLine(`Grep "${pattern}"${inPart}`);
  }

  if (toolName === "find" || toolName === "fffind") {
    const query =
      typeof args?.pattern === "string"
        ? singleLine(args.pattern, 32)
        : typeof args?.query === "string"
          ? singleLine(args.query, 32)
          : "";
    const inPart = pathVal ? ` in ${pathVal}` : "";
    return singleLine(`Find ${query || "*"}${inPart}`);
  }

  if (toolName === "ls") {
    return singleLine(`Ls ${pathVal || "."}`);
  }

  if (toolName === "web_search") {
    const query = typeof args?.query === "string" ? singleLine(args.query, 44) : "";
    return singleLine(`Search "${query}"`);
  }

  if (toolName === "web_fetch" || toolName === "fetch_content") {
    const url = typeof args?.url === "string" ? singleLine(args.url, 56) : "";
    return singleLine(`Fetch ${url}`);
  }

  if (toolName.startsWith("mcp__")) {
    const parts = toolName.slice(5).split("__");
    const displayName = parts.length >= 2 ? `${parts[0]}/${parts.slice(1).join("_")}` : toolName;
    const hint = firstArgValue(args, cwd);
    return singleLine(hint ? `${displayName} ${hint}` : displayName);
  }

  const hint = firstArgValue(args, cwd);
  return singleLine(hint ? `${toolName} ${hint}` : toolName);
}

function textOf(result: ToolResult): string {
  return stripAnsi(
    (result.content ?? [])
      .filter((block) => block.type === "text")
      .map((block) => block.text ?? "")
      .join("\n"),
  );
}

function lineCount(text: string): number {
  return text ? text.split("\n").filter((line) => line.trim() !== "").length : 0;
}

function lastLines(text: string, count: number): string {
  const lines = text.split("\n").filter((line) => line.trim() !== "");
  return lines.slice(-count).join("\n");
}

function firstNonEmptyLine(text: string): string {
  return text.split("\n").find((line) => line.trim() !== "") ?? "";
}

function durationSuffix(context: RenderContext | undefined): string {
  const ms = context?.durationMs;
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
    const message = singleLine(firstNonEmptyLine(body) || "失败", 48);
    return { ok: false, headline: message, body };
  }
  const details = result.details;
  const notices: string[] = [];
  if (details?.matchLimitReached) notices.push(`命中上限 ${details.matchLimitReached}`);
  if (details?.resultLimitReached) notices.push(`结果上限 ${details.resultLimitReached}`);
  if (details?.entryLimitReached) notices.push(`条目上限 ${details.entryLimitReached}`);
  if (details?.truncation?.truncated) notices.push("输出已截断");
  if (details?.linesTruncated) notices.push("长行已截断");

  const spec = LIST_TOOLS[tool];
  const empty = body === spec.emptyText;
  const headline = empty ? spec.emptyLabel : `${lineCount(body)} ${spec.unit}`;
  return {
    ok: true,
    headline,
    body: empty ? "" : body,
    notice: notices.length > 0 ? notices.join(" · ") : undefined,
  };
}

function summarizeRead(result: ToolResult, raw: string, isError: boolean): Summary {
  if (isError) {
    return { ok: false, headline: singleLine(firstNonEmptyLine(raw) || "失败", 48), body: raw };
  }
  const hasImage = (result.content ?? []).some((block) => block.type === "image");
  if (hasImage && !raw) {
    return { ok: true, headline: "图片", body: "" };
  }
  const body = raw.replace(LIST_NOTICE, "").trim();
  const count = lineCount(body);
  const notice = result.details?.truncation?.truncated ? "已截断" : undefined;
  return {
    ok: true,
    headline: count > 0 ? `${count} 行` : "空文件",
    body,
    notice,
  };
}

function countDiffLines(diffText: string, unified: boolean): { added: number; removed: number } {
  let added = 0;
  let removed = 0;
  const addRe = unified ? /^\+(?!\+\+)/ : /^\s*\+(?!\+\+)/;
  const delRe = unified ? /^-(?!--)/ : /^\s*-(?!--)/;
  for (const line of stripAnsi(diffText).split("\n")) {
    if (addRe.test(line)) added += 1;
    else if (delRe.test(line)) removed += 1;
  }
  return { added, removed };
}

function summarizeEdit(result: ToolResult, raw: string, isError: boolean): Summary {
  const diffBody = stripAnsi(result.details?.diff || result.details?.patch || raw).trim();
  if (isError) {
    return { ok: false, headline: singleLine(firstNonEmptyLine(raw) || "失败", 48), body: diffBody };
  }
  const patch = result.details?.patch;
  const diff = result.details?.diff;
  const stats = patch
    ? countDiffLines(patch, true)
    : diff
      ? countDiffLines(diff, false)
      : { added: 0, removed: 0 };
  const headline =
    stats.added > 0 || stats.removed > 0 ? `+${stats.added}/-${stats.removed}` : "已更新";
  return { ok: true, headline, body: diffBody };
}

function summarizeWrite(
  raw: string,
  isError: boolean,
  args: Record<string, unknown> | undefined,
): Summary {
  if (isError) {
    return { ok: false, headline: singleLine(firstNonEmptyLine(raw) || "失败", 48), body: raw };
  }
  const content = typeof args?.content === "string" ? stripAnsi(args.content) : "";
  const count = content ? content.split("\n").length : 0;
  return {
    ok: true,
    headline: count > 0 ? `${count} 行` : "已写入",
    body: content || raw,
  };
}

function summarizeGeneric(raw: string, isError: boolean): Summary {
  if (isError) {
    return { ok: false, headline: singleLine(firstNonEmptyLine(raw) || "失败", 48), body: raw };
  }
  const count = lineCount(raw);
  if (count === 0) {
    return { ok: true, headline: "完成", body: "" };
  }
  const first = singleLine(firstNonEmptyLine(raw), MAX_INLINE_RESULT_LEN + 1);
  if (count === 1 && first.length <= MAX_INLINE_RESULT_LEN) {
    return { ok: true, headline: first, body: raw };
  }
  return { ok: true, headline: `${count} 行`, body: raw };
}

function summarize(
  tool: string,
  result: ToolResult,
  isError: boolean,
  args: Record<string, unknown> | undefined,
): Summary {
  const raw = textOf(result).trim();
  if (tool === "bash") return summarizeBash(result, raw, isError);
  if (tool in LIST_TOOLS) return summarizeList(tool, result, raw, isError);
  if (tool === "read") return summarizeRead(result, raw, isError);
  if (tool === "edit") return summarizeEdit(result, raw, isError);
  if (tool === "write") return summarizeWrite(raw, isError, args);
  return summarizeGeneric(raw, isError);
}

export default function (pi: ExtensionAPI) {
  const activeTools = new Map<string, string>();

  function applyUiPreferences(ctx: UiContext | undefined) {
    if (!ctx?.hasUI) return;
    if (outputMode === "off") {
      ctx.ui?.setHiddenThinkingLabel?.();
      ctx.ui?.setWorkingMessage?.();
    } else {
      ctx.ui?.setHiddenThinkingLabel?.("");
    }
  }

  function syncWorkingMessage(ctx: UiContext | undefined) {
    if (!ctx?.hasUI) return;
    if (outputMode !== "quiet" || activeTools.size === 0) {
      ctx.ui?.setWorkingMessage?.();
      return;
    }
    const labels = [...activeTools.values()];
    const current = labels[labels.length - 1];
    const suffix = labels.length > 1 ? ` (+${labels.length - 1})` : "";
    ctx.ui?.setWorkingMessage?.(`${current}${suffix}`);
  }

  pi.on("session_start", (_event, ctx) => {
    activeTools.clear();
    applyUiPreferences(ctx as UiContext);
    syncWorkingMessage(ctx as UiContext);
  });

  pi.on("tool_execution_start", (event, ctx) => {
    if (event.parentToolCallId || PASSTHROUGH_TOOLS.has(event.toolName)) return;
    const uiCtx = ctx as UiContext | undefined;
    activeTools.set(
      event.toolCallId,
      formatCallLabel(event.toolName, event.args as Record<string, unknown> | undefined, uiCtx?.cwd),
    );
    syncWorkingMessage(uiCtx);
  });

  pi.on("tool_execution_end", (event, ctx) => {
    activeTools.delete(event.toolCallId);
    syncWorkingMessage(ctx as UiContext);
  });

  pi.on("agent_end", (_event, ctx) => {
    activeTools.clear();
    syncWorkingMessage(ctx as UiContext);
  });

  pi.registerCommand("compact-output", {
    description: "Switch tool & thinking output mode (quiet/compact/off/status)",
    handler: async (args: string, ctx: UiContext) => {
      const arg = (args ?? "").trim().toLowerCase();
      if (arg === "quiet" || arg === "on") outputMode = "quiet";
      else if (arg === "compact" || arg === "line") outputMode = "compact";
      else if (arg === "off") outputMode = "off";
      else if (arg !== "status") {
        outputMode = outputMode === "quiet" ? "compact" : outputMode === "compact" ? "off" : "quiet";
      }
      applyUiPreferences(ctx);
      syncWorkingMessage(ctx);
      ctx?.ui?.notify?.(`compact-output: ${outputMode}`, "info");
    },
  });

  pi.registerToolRenderer((toolName, next) => {
    if (outputMode === "off" || PASSTHROUGH_TOOLS.has(toolName)) return next();
    const base = next();
    return {
      renderShell: "self" as const,
      renderCall(args, theme, context) {
        if (outputMode === "off" && base?.renderCall) {
          return base.renderCall(args, theme, context);
        }
        const ctx = context as RenderContext | undefined;
        const state = ctx?.state as { callText?: Text } | undefined;
        if (outputMode === "quiet" && !ctx?.expanded) {
          if (state) state.callText = undefined;
          return EMPTY_COMPONENT;
        }
        const label = formatCallLabel(toolName, args as Record<string, unknown> | undefined, ctx?.cwd);
        const line = (theme as Theme).fg("muted", `… ${label}`);
        if (state?.callText && typeof state.callText.setText === "function") {
          state.callText.setText(line);
          return state.callText;
        }
        const text = new Text(line, 0, 0);
        if (state) state.callText = text;
        return text;
      },
      renderResult(result, options, theme, context) {
        if (outputMode === "off" && base?.renderResult) {
          return base.renderResult(result, options, theme, context);
        }
        const opts = (options ?? {}) as RenderOptions;
        const ctx = context as RenderContext | undefined;
        const typedTheme = theme as Theme;
        const state = ctx?.state as { callText?: Text } | undefined;
        const callText = state?.callText;
        const hasCallSlot = Boolean(callText && typeof callText.setText === "function");

        if (opts.isPartial) {
          if (outputMode === "quiet" && !opts.expanded) {
            return EMPTY_COMPONENT;
          }
          return hasCallSlot ? EMPTY_COMPONENT : new Text(typedTheme.fg("muted", "… 运行中"), 0, 0);
        }

        const label = formatCallLabel(toolName, ctx?.args, ctx?.cwd);
        const summary = summarize(toolName, result as ToolResult, ctx?.isError === true, ctx?.args);
        const duration = durationSuffix(ctx);
        const noticePart = summary.notice ? ` · ${summary.notice}` : "";
        const headline = summary.ok
          ? typedTheme.fg("success", `✓ ${label} · ${summary.headline}${noticePart}${duration}`)
          : typedTheme.fg("error", `✗ ${label} ${summary.headline}${duration}`);

        if (hasCallSlot) {
          callText!.setText(headline);
        }

        if (opts.expanded) {
          let outputComp: { render: (width: number) => string[]; invalidate: () => void } | undefined;
          if (base?.renderResult) {
            try {
              const nativeComp = base.renderResult(result, options, theme, context);
              if (nativeComp) outputComp = nativeComp;
            } catch {
              // 原生渲染失败时回退到纯文本输出
            }
          }

          const expandedCommand =
            toolName === "bash" && typeof ctx?.args?.command === "string"
              ? stripAnsi(ctx.args.command).trim()
              : "";

          if (expandedCommand) {
            const container = new Container();
            if (!hasCallSlot) {
              container.addChild(new Text(headline, 0, 0));
            }
            container.addChild(
              new Text(typedTheme.fg("muted", `$ ${expandedCommand}`), hasCallSlot ? 2 : 0, 0),
            );
            if (outputComp) {
              container.addChild(outputComp);
            } else if (summary.body) {
              container.addChild(
                new Text(typedTheme.fg("toolOutput", summary.body), hasCallSlot ? 2 : 0, 0),
              );
            }
            return container;
          }

          if (outputComp) {
            if (!hasCallSlot) {
              const container = new Container();
              container.addChild(new Text(headline, 0, 0));
              container.addChild(outputComp);
              return container;
            }
            return outputComp;
          }

          const bodyText = summary.body ? typedTheme.fg("toolOutput", summary.body) : "";
          if (!hasCallSlot) {
            return new Text(bodyText ? `${headline}\n${bodyText}` : headline, 0, 0);
          }
          return bodyText ? new Text(bodyText, 2, 0) : EMPTY_COMPONENT;
        }

        if (summary.ok) {
          if (outputMode === "quiet") {
            return EMPTY_COMPONENT;
          }
          return hasCallSlot ? EMPTY_COMPONENT : new Text(headline, 0, 0);
        }

        const tail = lastLines(summary.body, FAILURE_TAIL_LINES);
        if (hasCallSlot) {
          return tail ? new Text(typedTheme.fg("toolOutput", tail), 2, 0) : EMPTY_COMPONENT;
        }
        return new Text(tail ? `${headline}\n${typedTheme.fg("toolOutput", tail)}` : headline, 0, 0);
      },
    };
  });
}
