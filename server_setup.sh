#!/bin/bash
# BRAiN Remote Server Setup
# Creates Claude user and deployment structure
# Run as root on brain.falklabs.de

set -e

echo "========================================"
echo "BRAiN Remote Server Setup"
echo "========================================"
echo ""

# Configuration
CLAUDE_USER="claude"
SERVER_HOST="brain.falklabs.de"
SSH_PORT=22

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}[1/6] Creating Claude user...${NC}"

# Create claude user if not exists
if id "$CLAUDE_USER" &>/dev/null; then
    echo "✓ User $CLAUDE_USER already exists"
else
    useradd -m -s /bin/bash $CLAUDE_USER
    echo "✓ User $CLAUDE_USER created"
fi

# Add to necessary groups
usermod -aG sudo $CLAUDE_USER
usermod -aG docker $CLAUDE_USER
echo "✓ Added to groups: sudo, docker"

echo ""
echo -e "${YELLOW}[2/6] Setting up SSH access...${NC}"

# Create .ssh directory
CLAUDE_HOME="/home/$CLAUDE_USER"
mkdir -p $CLAUDE_HOME/.ssh
chmod 700 $CLAUDE_HOME/.ssh

# Generate SSH key pair for Claude
if [ ! -f "$CLAUDE_HOME/.ssh/id_ed25519" ]; then
    ssh-keygen -t ed25519 -C "claude@brain.falklabs.de" -f $CLAUDE_HOME/.ssh/id_ed25519 -N ""
    echo "✓ SSH key pair generated"
else
    echo "✓ SSH key pair already exists"
fi

# Create authorized_keys
touch $CLAUDE_HOME/.ssh/authorized_keys
chmod 600 $CLAUDE_HOME/.ssh/authorized_keys

# Set ownership
chown -R $CLAUDE_USER:$CLAUDE_USER $CLAUDE_HOME/.ssh

echo ""
echo -e "${GREEN}Public key for Claude user:${NC}"
cat $CLAUDE_HOME/.ssh/id_ed25519.pub
echo ""
echo -e "${YELLOW}Save this public key - you'll need it for GitHub deploy keys!${NC}"
echo ""

echo -e "${YELLOW}[3/6] Creating deployment directories...${NC}"

# Create deployment paths
for env in dev stage prod; do
    DIR="/srv/$env"
    if [ ! -d "$DIR" ]; then
        mkdir -p $DIR
        chown $CLAUDE_USER:$CLAUDE_USER $DIR
        chmod 755 $DIR
        echo "✓ Created $DIR"
    else
        echo "✓ $DIR already exists"
    fi
done

echo ""
echo -e "${YELLOW}[4/6] Installing required tools...${NC}"

# Update package list
apt-get update -qq

# Install essential tools
PACKAGES=(
    "git"
    "docker.io"
    "docker-compose"
    "python3-pip"
    "nginx"
    "certbot"
    "python3-certbot-nginx"
)

for pkg in "${PACKAGES[@]}"; do
    if dpkg -l | grep -q "^ii  $pkg "; then
        echo "✓ $pkg already installed"
    else
        apt-get install -y $pkg > /dev/null 2>&1
        echo "✓ Installed $pkg"
    fi
done

echo ""
echo -e "${YELLOW}[5/6] Configuring Git for Claude user...${NC}"

# Configure git for claude user
su - $CLAUDE_USER << 'EOF'
git config --global user.name "Claude AI"
git config --global user.email "claude@brain.falklabs.de"
git config --global init.defaultBranch main
echo "✓ Git configured"
EOF

echo ""
echo -e "${YELLOW}[6/6] Setting up sudo permissions...${NC}"

# Allow claude to run deployment commands without password
cat > /etc/sudoers.d/claude << 'SUDOERS'
# Claude user - deployment permissions
claude ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart brain-*
claude ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop brain-*
claude ALL=(ALL) NOPASSWD: /usr/bin/systemctl start brain-*
claude ALL=(ALL) NOPASSWD: /usr/bin/systemctl status brain-*
claude ALL=(ALL) NOPASSWD: /usr/bin/docker-compose
claude ALL=(ALL) NOPASSWD: /usr/bin/docker
claude ALL=(ALL) NOPASSWD: /usr/bin/nginx -t
claude ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
SUDOERS

chmod 440 /etc/sudoers.d/claude
echo "✓ Sudo permissions configured"

echo ""
echo "========================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo "========================================"
echo ""
echo "Summary:"
echo "  User created: $CLAUDE_USER"
echo "  SSH key: $CLAUDE_HOME/.ssh/id_ed25519"
echo "  Deployment paths:"
echo "    - /srv/dev/"
echo "    - /srv/stage/"
echo "    - /srv/prod/"
echo ""
echo "Next steps:"
echo "  1. Copy public key to GitHub as deploy key"
echo "  2. Configure GitHub SSH access"
echo "  3. Test SSH connection: ssh claude@$SERVER_HOST"
echo "  4. Run deployment scripts"
echo ""
echo -e "${YELLOW}SSH Public Key (save this!):${NC}"
cat $CLAUDE_HOME/.ssh/id_ed25519.pub
echo ""
