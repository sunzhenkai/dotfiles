# Module 三段式：注册表 + Handler + Executor，新增模块双触点

新增一个 Module 曾要碰四处：modules.yaml 注册、scripts/modules/<name>/ Handler、scripts/tools/<name>.sh 辅助函数、config/<category>/<name>/ 配置源，同属一个模块的代码散在两层。决定固定 Module 解剖为三段式——modules.yaml 一条注册（含 config 声明）、scripts/modules/<name>/ 目录内 Handler、通用 Executor 调度——并把 scripts/tools/<name>.sh 并入各自 Handler 目录；config/<category>/ 分类树与部署 source 保留不动。否决了「每模块自包含目录、config 随迁」的聚合方案：它丢掉 config 分类导航，且纯配置模块（starship 只有 copy）与纯安装模块（homebrew 只有安装）会出现空目录或不对称结构。此后新增模块只允许两个触点：modules.yaml 一行 + Handler 目录。
