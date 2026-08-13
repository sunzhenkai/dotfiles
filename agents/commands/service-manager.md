---
id: service-manager
title: "服务管理"
description: 探索项目服务启动方式（Makefile / package.json / docker-compose），执行 list / start / stop / restart / status / logs；缓存加速启动，并把启动信息与踩坑写入 .service-manager.md
category: Workflow
tags: [service, dev, workflow]
---

管理当前项目的服务生命周期。

面向用户的输出默认使用简体中文。命令名、路径、代码、状态值与既成术语保持原文，不要逐词硬翻。

**输入**：phase（`list` / `start` / `stop` / `restart` / `status` / `logs`）+ 可选服务名与行数。缺省 phase 为 `list`。

## 步骤

1. 先读项目根 `.service-manager.md`（若有）与缓存 `~/.cache/service-manager/<md5(项目路径)>.json`；缓存失效则 discover（Makefile / package.json / docker-compose 等）并回写缓存
2. discover 或启动成功后，把启动相关信息写入/更新 `.service-manager.md`（服务 command、cwd、port、前置条件）；**遇到坑立刻追加到「踩坑」节**
3. 按 phase 执行：list 输出服务清单与状态；start 后台启动并记录 pid/日志；stop 校验进程身份后 kill；restart = stop + start；status 查进程与端口；logs tail 日志
4. 探索不出启动方式或进程身份对不上时，停下来问用户，不猜命令、不猜杀

详细约定见 skill `service-manager`。
