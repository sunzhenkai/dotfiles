// /exit 命令：退出 pi
// 下发位置：~/.pi/agent/extensions/exit.ts（dotf pi -c）
export default function (pi: any) {
  pi.registerCommand("exit", {
    description: "Quit pi",
    handler: async (_args: string, ctx: any) => {
      ctx.shutdown();
    },
  });
}
