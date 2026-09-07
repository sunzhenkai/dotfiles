# 模块生命周期增加 uninstall 与 deconfig

现有动作只有 install / config / doctor，TUI 若用同一个「卸载」按钮同时撤软件和配置，会卸错对象（例如把只有 config 的 nvim 当成软件包）。模块反动作与正动作对称：`uninstall` 撤 install，`deconfig` 撤 config；双能力模块并列两项，不合并。有 Dependent 在场时拒绝 uninstall，不级联。deconfig 沿用已有所有权：只撤未漂的 owned 目标，Conflict 留下。
