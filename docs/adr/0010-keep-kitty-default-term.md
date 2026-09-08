# Kitty 保持默认 TERM=xterm-kitty

把 `term` 改成 `xterm-256color` 能让没装 Kitty terminfo 的远程机立刻跑 vim/less/htop，但会关掉 Kitty 图形协议。Yazi 按 `$TERM` 选图像后端，匹配不到 Kgp 就落到 Chafa 字符画。决定不覆盖 TERM：本机保持默认 `xterm-kitty`，远程缺 terminfo 时装发行版的 `kitty-terminfo`（或用 `kitten ssh` 播种到远端家目录），而不是在本机降级终端类型。
