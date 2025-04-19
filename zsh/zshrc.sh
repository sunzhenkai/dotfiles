# starship
command -v starship >/dev/null && eval "$(starship init zsh)"

# env init
ENV_INIT_DIR="$HOME/.local/env-init/env"
if [[ -e "$ENV_INIT_DIR" ]]; then
  source "$ENV_INIT_DIR"
  alias ienv="source $ENV_INIT_DIR"
fi
