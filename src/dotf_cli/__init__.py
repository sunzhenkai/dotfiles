"""用户面 CLI：参数解析 + 子命令路由，不含业务逻辑。

业务实现委托既有工具（dotf_core.registry / dotf_core.planner / agents.skills_map /
run_plan.sh 等），本包只做命令面：解析、守卫、输出与错误契约。
"""
