// 全工具无框单行紧凑渲染：成功只留一行摘要，失败附末 3 行，展开（Ctrl+O）看完整详情。
// 只替换 renderResult / renderCall（并设 renderShell: "self"），不重注册工具、不影响模型上下文。
// 支持 /compact-output [on|off|status] 运行时切换；用户问答工具直通原生渲染。
// 下发位置：~/.pi/agent/extensions/compact-output.ts（dotf pi -c）
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Text } from "@earendil-works/pi-tui";

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
const LEADING_CD = /^cd\s+(?:(?:"([^"]+)"|'([^']+)'|([^\s;&|]+)))\s*(?:&&|;|\n)\s*([\s\S]+)$/;
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

let compactEnabled = true;

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

function normalizeDir(dir: string): string {
  let value = dir.trim();
  const home = typeof process !== "undefined" ? process.env?.HOME : undefined;
  if (home) {
    const cleanHome = home.length > 1 ? home.replace(/\/+$/, "") : home;
    if (value === "~") value = cleanHome;
    else if (value.startsWith("~/")) value = `${cleanHome}/${value.slice(2)}`;
  }
  if (value.length > 1) {
    value = value.replace(/\/+$/, "");
  }
  return value;
}

function resolveEffectiveCwd(cwd?: string): string | undefined {
  if (cwd && cwd.trim()) return cwd.trim();
  if (typeof process !== "undefined" && typeof process.cwd === "function") {
    try {
      return process.cwd();
    } catch {
      return undefined;
    }
  }
  return undefined;
}

function compactDirLabel(rawTarget: string, effectiveCwd?: string): string {
  const target = normalizeDir(rawTarget);
  if (effectiveCwd) {
    const normCwd = normalizeDir(effectiveCwd);
    const prefix = normCwd === "/" ? "/" : `${normCwd}/`;
    if (target.startsWith(prefix)) {
      const rel = target.slice(prefix.length);
      if (rel && rel.length <= 24) return rel;
    }
  }
  const home = typeof process !== "undefined" ? process.env?.HOME : undefined;
  if (home && target === normalizeDir(home)) return "~";
  if (target === "/") return "/";
  const parts = target.split("/").filter(Boolean);
  return parts[parts.length - 1] ?? target;
}

function formatBashCall(rawCommand: unknown, cwd?: string): string {
  if (typeof rawCommand !== "string") return "$ (empty)";
  const cleaned = stripAnsi(rawCommand).trim();
  if (!cleaned) return "$ (empty)";

  const match = LEADING_CD.exec(cleaned);
  if (match) {
    const rawTarget = (match[1] ?? match[2] ?? match[3] ?? "").trim();
    const rest = (match[4] ?? "").trim();
    if (rawTarget && rest && !rawTarget.startsWith("-")) {
      const effectiveCwd = resolveEffectiveCwd(cwd);
      const isSameDir =
        rawTarget === "." ||
        rawTarget === "./" ||
        rawTarget === "$PWD" ||
        rawTarget === "${PWD}" ||
        (effectiveCwd !== undefined && normalizeDir(rawTarget) === normalizeDir(effectiveCwd));
      if (isSameDir) {
        return singleLine(`$ ${rest}`);
      }
      const dirLabel = compactDirLabel(rawTarget, effectiveCwd);
      return singleLine(`[${dirLabel}] $ ${rest}`);
    }
  }

  return singleLine(`$ ${cleaned}`);
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
    return formatBashCall(args?.command, cwd);
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
  pi.registerCommand("compact-output", {
    description: "Toggle compact single-line tool output (on/off/status)",
    handler: async (args: string, ctx: { ui?: { notify?: (msg: string, level?: string) => void } }) => {
      const arg = (args ?? "").trim().toLowerCase();
      if (arg === "on") compactEnabled = true;
      else if (arg === "off") compactEnabled = false;
      else if (arg !== "status") compactEnabled = !compactEnabled;
      ctx?.ui?.notify?.(`compact-output: ${compactEnabled ? "on" : "off"}`, "info");
    },
  });

  pi.registerToolRenderer((toolName, next) => {
    if (!compactEnabled || PASSTHROUGH_TOOLS.has(toolName)) return next();
    const base = next();
    return {
      renderShell: "self" as const,
      renderCall(args, theme, context) {
        if (!compactEnabled && base?.renderCall) {
          return base.renderCall(args, theme, context);
        }
        const ctx = context as RenderContext | undefined;
        const label = formatCallLabel(toolName, args as Record<string, unknown> | undefined, ctx?.cwd);
        const line = (theme as Theme).fg("muted", `… ${label}`);
        const state = ctx?.state as { callText?: Text } | undefined;
        if (state?.callText && typeof state.callText.setText === "function") {
          state.callText.setText(line);
          return state.callText;
        }
        const text = new Text(line, 0, 0);
        if (state) state.callText = text;
        return text;
      },
      renderResult(result, options, theme, context) {
        if (!compactEnabled && base?.renderResult) {
          return base.renderResult(result, options, theme, context);
        }
        const opts = (options ?? {}) as RenderOptions;
        const ctx = context as RenderContext | undefined;
        const typedTheme = theme as Theme;
        const state = ctx?.state as { callText?: Text } | undefined;
        const callText = state?.callText;
        const hasCallSlot = Boolean(callText && typeof callText.setText === "function");

        if (opts.isPartial) {
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
          if (base?.renderResult) {
            try {
              const nativeComp = base.renderResult(result, options, theme, context);
              if (nativeComp) return nativeComp;
            } catch {
              // 原生渲染失败时回退到纯文本输出
            }
          }
          const bodyText = summary.body ? typedTheme.fg("toolOutput", summary.body) : "";
          if (!hasCallSlot) {
            return new Text(bodyText ? `${headline}\n${bodyText}` : headline, 0, 0);
          }
          return bodyText ? new Text(bodyText, 2, 0) : EMPTY_COMPONENT;
        }

        if (summary.ok) {
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
