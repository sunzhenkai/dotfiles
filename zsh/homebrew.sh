# Homebrew 环境变量自动配置
# 自动为所有 keg-only 软件包设置环境变量

# 设置 Homebrew 基础路径
if [[ -d "/home/linuxbrew/.linuxbrew" ]]; then
    export HOMEBREW_PREFIX="/home/linuxbrew/.linuxbrew"
elif [[ -d "$HOME/.linuxbrew" ]]; then
    export HOMEBREW_PREFIX="$HOME/.linuxbrew"
elif [[ -d "/opt/homebrew" ]]; then
    export HOMEBREW_PREFIX="/opt/homebrew"
elif [[ -d "$HOME/.brew" ]]; then
    export HOMEBREW_PREFIX="$HOME/.brew"
fi

# 如果没有找到 Homebrew 路径，跳过后续配置
if [[ -z "$HOMEBREW_PREFIX" ]] || [[ ! -d "$HOMEBREW_PREFIX" ]]; then
    return 0
fi

# 将 Homebrew bin 加入 PATH
export PATH="$HOMEBREW_PREFIX/bin:$HOMEBREW_PREFIX/sbin:$PATH"

# 自动为所有已安装的 keg-only 软件包设置编译器和 pkg-config 变量
_hbrew_add_keg_variables() {
    local keg prefix
    local -a bins libs includes pkgconfigs

    # 遍历 opt 目录下的所有软件包
    for keg in "$HOMEBREW_PREFIX/opt"/*; do
        [[ -d "$keg" ]] || continue
        prefix="$keg"

        # 查找 bin 目录，加入 PATH
        if [[ -d "$prefix/bin" ]]; then
            bins+=("$prefix/bin")
        fi
        if [[ -d "$prefix/sbin" ]]; then
            bins+=("$prefix/sbin")
        fi

        # 查找 lib 目录，加入 LDFLAGS
        if [[ -d "$prefix/lib" ]]; then
            libs+=("-L$prefix/lib")
        fi

        # 查找 include 目录，加入 CPPFLAGS
        if [[ -d "$prefix/include" ]]; then
            includes+=("-I$prefix/include")
        fi

        # 查找 pkgconfig 目录，加入 PKG_CONFIG_PATH
        if [[ -d "$prefix/lib/pkgconfig" ]]; then
            pkgconfigs+=("$prefix/lib/pkgconfig")
        elif [[ -d "$prefix/lib/cmake" ]]; then
            pkgconfigs+=("$prefix/lib/cmake")
        fi
    done

    # 添加 bin 路径到 PATH（去重，优先靠前）
    local -U path_arr
    for bin in "${bins[@]}"; do
        path_arr+=("$bin")
    done
    for p in "${path_arr[@]}"; do
        if [[ ":$PATH:" != *":$p:"* ]]; then
            export PATH="$p:$PATH"
        fi
    done

    # 添加库路径到 LDFLAGS（去重）
    local -U ldflags_arr
    for lib in "${libs[@]}"; do
        ldflags_arr+=("$lib")
    done
    local ldflags_str
    ldflags_str="${(j: :)ldflags_arr}"
    if [[ -n "$ldflags_str" ]]; then
        export LDFLAGS="$ldflags_str ${LDFLAGS:-}"
    fi

    # 添加头文件路径到 CPPFLAGS（去重）
    local -U cppflags_arr
    for inc in "${includes[@]}"; do
        cppflags_arr+=("$inc")
    done
    local cppflags_str
    cppflags_str="${(j: :)cppflags_arr}"
    if [[ -n "$cppflags_str" ]]; then
        export CPPFLAGS="$cppflags_str ${CPPFLAGS:-}"
    fi

    # 添加 pkgconfig 路径到 PKG_CONFIG_PATH（去重）
    local -U pkgconfig_arr
    for pc in "${pkgconfigs[@]}"; do
        pkgconfig_arr+=("$pc")
    done
    local pkgconfig_str
    pkgconfig_str="${(j: :)pkgconfig_arr}"
    if [[ -n "$pkgconfig_str" ]]; then
        export PKG_CONFIG_PATH="$pkgconfig_str:${PKG_CONFIG_PATH:-}"
    fi
}

# 执行配置
_hbrew_add_keg_variables

# 清理函数
unset -f _hbrew_add_keg_variables
