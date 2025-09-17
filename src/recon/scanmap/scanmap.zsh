# Bash completion for nmap_batch.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST_ZSH="$HOME/.oh-my-zsh/custom/scanmap.zsh"
_scanmap_complete() {
  local cur prev opts
  COMPREPLY=()
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]}"

  # Options that the script supports
  opts="--targets --prefix --outdir"

  case "$prev" in
    --targets|--outdir)
      # Complete directories or files for targets/outdir
      COMPREPLY=( $(compgen -f -- "$cur") )
      return 0
      ;;
    --prefix)
      # No file completion for prefix
      return 0
      ;;
    *)
      if [[ "$cur" == -* ]]; then
        COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
        return 0
      fi
      ;;
  esac
}

_update_scanmap() {
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  export SCRIPT_DIR_BAK="$SCRIPT_DIR"
  git -C "$SCRIPT_DIR" pull
  cp "$SCRIPT_DIR_BAK"/scanmap.zsh ~/.oh-my-zsh/custom/scanmap.zsh
  sed -i "s|^SCRIPT_DIR=.*|SCRIPT_DIR=\"$SCRIPT_DIR_BAK\"|" "$DEST_ZSH"
  source ~/.zshrc
}

# Register the function for your script name
complete -F _scanmap_complete scanmap
alias scanmap_update="_update_scanmap"
