#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Setting up scanmap..."
LINE='export PATH="$PATH:/home/$USER/.local/bin"'
ZSHRC="$HOME/.zshrc"

# Create local bin and symlink scanmap.sh
mkdir -p /home/$(whoami)/.local/bin
ln -sf "$SCRIPT_DIR/scanmap.sh" /home/$(whoami)/.local/bin/scanmap
chmod +x /home/$(whoami)/.local/bin/scanmap

# Copy scanmap.zsh to oh-my-zsh custom directory
DEST_ZSH="$HOME/.oh-my-zsh/custom/scanmap.zsh"
cp "$SCRIPT_DIR/scanmap.zsh" "$DEST_ZSH"

# Update SCRIPT_DIR= line in scanmap.zsh to use the current $SCRIPT_DIR
sed -i "s|^SCRIPT_DIR=.*|SCRIPT_DIR=\"$SCRIPT_DIR\"|" "$DEST_ZSH"

# Add PATH line to .zshrc if not already present
if ! grep -Fxq "$LINE" "$ZSHRC"; then
  echo "$LINE" >> "$ZSHRC"
fi
