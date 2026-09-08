# Skill 以机器为粒度，MCP Entry 默认按工具

一手 skill 装在共享 `~/.agents/skills`，没有稳定的按工具分发面；v1 的 apply/remove 对这台机器上所有读取该目录的工具生效，Kiro 镜像跟同一 Desired Set。MCP 的本机存在是各工具自己的结构化文件里的一条 Entry，默认按工具 exclude；要全工具去掉必须显式选「本机全部工具」。
