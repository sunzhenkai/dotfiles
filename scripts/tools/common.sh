#!/bin/bash
# 公共工具函数

# 确认函数
# 参数: $1=提示信息, $2=默认值(Y/N, 默认Y)
# 返回: 0=用户确认, 1=用户拒绝
confirm() {
  local prompt="$1"
  local default="${2:-Y}"
  local reply

  if [[ "$default" == "Y" ]]; then
    read -r -p "$prompt [Y/n]: " reply
    [[ -z "$reply" || "$reply" =~ ^[Yy] ]]
  else
    read -r -p "$prompt [y/N]: " reply
    [[ "$reply" =~ ^[Yy] ]]
  fi
}
