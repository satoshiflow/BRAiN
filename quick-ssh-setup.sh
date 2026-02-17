#!/bin/bash
# Quick SSH Setup Script für Claude Code
# Führe dies auf brain.falklabs.de aus

echo "🔐 SSH Setup für Claude Code"
echo "============================"

# Als claude user arbeiten
if [ "$USER" != "claude" ]; then
    echo "⚠️  Wechsle zu claude user..."
    sudo su - claude << 'CLAUDE_USER'

# Ab hier als claude user
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Generiere SSH Key
echo "🔑 Generiere SSH Key..."
ssh-keygen -t ed25519 -C "claude-code@brain.falklabs.de" -f ~/.ssh/claude_code_key -N ""

# Füge zu authorized_keys hinzu
cat ~/.ssh/claude_code_key.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

echo ""
echo "✅ SSH Key erstellt!"
echo ""
echo "📋 KOPIERE DEN FOLGENDEN PRIVATE KEY:"
echo "======================================"
cat ~/.ssh/claude_code_key
echo "======================================"
echo ""
echo "👉 Gib diesen Private Key an Claude Code weiter"

CLAUDE_USER
else
    # Bereits als claude user
    mkdir -p ~/.ssh
    chmod 700 ~/.ssh

    ssh-keygen -t ed25519 -C "claude-code@brain.falklabs.de" -f ~/.ssh/claude_code_key -N ""
    cat ~/.ssh/claude_code_key.pub >> ~/.ssh/authorized_keys
    chmod 600 ~/.ssh/authorized_keys

    echo ""
    echo "✅ SSH Key erstellt!"
    echo ""
    echo "📋 KOPIERE DEN FOLGENDEN PRIVATE KEY:"
    echo "======================================"
    cat ~/.ssh/claude_code_key
    echo "======================================"
fi

# Docker Permissions (als root)
echo ""
echo "🐳 Füge claude zu docker Gruppe hinzu..."
sudo usermod -aG docker claude

echo ""
echo "✅ Setup komplett!"
echo ""
echo "🧪 TEST SSH Connection:"
echo "ssh claude@brain.falklabs.de 'hostname && whoami && docker ps | wc -l'"
