# alacritty-config

使用 dotf 将仓库声明配置安装为 HOME 下的真实目录：

```shell
dotf alacritty -c --dry-run
dotf alacritty -c --yes
```

不要直接克隆或链接到 `~/.config/alacritty`；该目标由 managed manifest 按 `copy` 策略维护。修改仓库配置后需重新运行 `dotf alacritty -c`。

# config

[Official Document](https://alacritty.org/config-alacritty.html)

# theme

[Official Themes](https://github.com/alacritty/alacritty-theme?tab=readme-ov-file)
