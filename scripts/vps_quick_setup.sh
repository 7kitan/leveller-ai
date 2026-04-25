#!/bin/bash
# =============================================================================
# VPS Quick Setup Script
# Tự động cài đặt và cấu hình VPS Ubuntu 22.04 cho Lumix AI
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Lumix AI - VPS Quick Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Please run as root (sudo)${NC}"
    exit 1
fi

# Step 1: Update system
echo -e "${YELLOW}[1/8] Updating system packages...${NC}"
apt update && apt upgrade -y
apt install -y curl wget git vim htop net-tools ufw

# Step 2: Configure firewall
echo -e "${YELLOW}[2/8] Configuring firewall...${NC}"
ufw --force enable
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw status

# Step 3: Install Docker
echo -e "${YELLOW}[3/8] Installing Docker...${NC}"
apt remove -y docker docker-engine docker.io containerd runc || true
apt install -y ca-certificates curl gnupg lsb-release

mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Configure Docker daemon
cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
EOF

systemctl restart docker
systemctl enable docker

# Step 4: Create deploy user
echo -e "${YELLOW}[4/8] Creating deploy user...${NC}"
if id "deploy" &>/dev/null; then
    echo "User 'deploy' already exists"
else
    adduser --disabled-password --gecos "" deploy
    usermod -aG sudo deploy
    usermod -aG docker deploy
    echo "deploy ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/deploy
fi

# Step 5: Setup directories
echo -e "${YELLOW}[5/8] Setting up directories...${NC}"
sudo -u deploy mkdir -p /home/deploy/projects
sudo -u deploy mkdir -p /home/deploy/backups
sudo -u deploy mkdir -p /home/deploy/.ssh
chmod 700 /home/deploy/.ssh

# Step 6: Install Nginx
echo -e "${YELLOW}[6/8] Installing Nginx...${NC}"
apt install -y nginx
systemctl enable nginx
systemctl start nginx

# Step 7: Install Certbot
echo -e "${YELLOW}[7/8] Installing Certbot...${NC}"
apt install -y certbot python3-certbot-nginx

# Step 8: Setup log rotation
echo -e "${YELLOW}[8/8] Configuring log rotation...${NC}"
cat > /etc/logrotate.d/docker-containers << 'EOF'
/var/lib/docker/containers/*/*.log {
    rotate 7
    daily
    compress
    size=10M
    missingok
    delaycompress
    copytruncate
}
EOF

# Generate secure passwords
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}📝 Generated Secure Values:${NC}"
echo ""
echo "JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
echo "REDIS_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
echo "POSTGRES_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
echo "REDIS_ENCRYPTION_KEY=$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
echo ""
echo -e "${YELLOW}⚠️  SAVE THESE VALUES! You'll need them for .env configuration${NC}"
echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo "1. Switch to deploy user: su - deploy"
echo "2. Clone repository: git clone https://github.com/a20-ai-thuc-chien/A20-App-078.git"
echo "3. Configure .env files with the values above"
echo "4. Run deployment script"
echo ""
echo -e "${GREEN}✅ VPS is ready for deployment!${NC}"
