# 源码密钥字面量被抄进模块页

- Date: 2026-08-28
- Kind: failure
- Skill: project-spec-mirror
- Context: detailed / important 整理模块文件表时，源码常量含 AppKey / SecretKey 一类凭据

## What happened

Agent 把源码里的鉴权常量赋值写进文件表「职责」或核心符号说明，镜像因此带上密钥原文。同时 important 把非重要文件整份省略，模块页信息过少。

## Lesson

- important 对范围内文件写简述，不得因「不重要」漏行。
- 凭据只写字段名与注入方式，值一律 `<REDACTED>`；产品标识不是密钥。
- 可复用于后续 build/update；已写入 modes 与公共执行契约。
