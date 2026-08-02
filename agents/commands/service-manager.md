---
id: service-manager
title: "Service Manager"
description: 探索项目服务启动方式（Makefile / package.json / docker-compose），执行 list / start / stop / restart / status / logs，缓存清单加速再次启动
category: Workflow
tags: [service, dev, workflow]
---

管理当前项目的服务生命周期。

**Input**：phase（`list` / `start` / `stop` / `restart` / `status` / `logs`）+ 可选服务名与行数。缺省 phase 为 `list`。

## 步骤

1. 读缓存 `~/.cache/service-manager/<md5(项目路径)>.json`；缓存失效则从 Makefile、package.json、docker-compose 等重新 discover 并回写缓存
2. 按 phase 执行：list 输出服务清单与状态；start 后台启动并记录 pid/日志；stop 校验进程身份后 kill；restart = stop + start；status 查进程与端口；logs tail 日志
3. 探索不出启动方式或进程身份对不上时，停下来问用户，不猜命令、不猜杀

详细约定见 skill `service-manager`。
