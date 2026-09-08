# uninstall 必须声明 handler，禁止猜测卸法

各模块装法不同，通用 `brew uninstall` 会卸错或卸底座。注册表要显式声明 `uninstall`；没有 handler 就没有该动作，TUI/CLI 不展示、不拼命令。deconfig 可以走已有 owned manifest 的通用撤回。v1 允许只有部分模块具备 uninstall。
