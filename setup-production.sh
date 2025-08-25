#!/bin/bash

# Production server setup script for Trello Connect Flow
set -e

echo "🚀 Setting up production server for Trello Connect Flow..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run this script as root (use sudo)"
    exit 1
fi

# Step 1: Update system packages
print_status "Updating system packages..."
apt update && apt upgrade -y

# Step 2: Install required packages
print_status "Installing required packages..."
apt install -y curl wget git nginx certbot python3-certbot-nginx ufw

# Step 3: Install Docker if not already installed
if ! command -v docker &> /dev/null; then
    print_status "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    usermod -aG docker $SUDO_USER
    rm get-docker.sh
else
    print_status "Docker is already installed"
fi

# Step 4: Install Docker Compose if not already installed
if ! command -v docker-compose &> /dev/null; then
    print_status "Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
else
    print_status "Docker Compose is already installed"
fi

# Step 5: Configure firewall
print_status "Configuring firewall..."
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80
ufw allow 443
ufw allow 5000  # For direct access if needed
print_status "Firewall configured"

# Step 6: Configure nginx
print_status "Configuring nginx..."
cp nginx.production.conf /etc/nginx/sites-available/boards.norgayhrconsulting.com.au
ln -sf /etc/nginx/sites-available/boards.norgayhrconsulting.com.au /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default  # Remove default site

# Test nginx configuration
if nginx -t; then
    print_status "Nginx configuration is valid"
    systemctl restart nginx
    systemctl enable nginx
else
    print_error "Nginx configuration is invalid"
    exit 1
fi

# Step 7: Set up SSL certificate
print_status "Setting up SSL certificate with Let's Encrypt..."
if certbot --nginx -d boards.norgayhrconsulting.com.au -d www.boards.norgayhrconsulting.com.au --non-interactive --agree-tos --email admin@norgayhrconsulting.com.au; then
    print_status "SSL certificate installed successfully"
else
    print_warning "SSL certificate setup failed. You can retry later with:"
    echo "certbot --nginx -d boards.norgayhrconsulting.com.au -d www.boards.norgayhrconsulting.com.au"
fi

# Step 8: Set up automatic SSL renewal
print_status "Setting up automatic SSL renewal..."
(crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -

# Step 9: Create application directory
print_status "Setting up application directory..."
mkdir -p /opt/trello-connect-flow
chown $SUDO_USER:$SUDO_USER /opt/trello-connect-flow

# Step 10: Set up log rotation
print_status "Setting up log rotation..."
cat > /etc/logrotate.d/trello-connect-flow << EOF
/opt/trello-connect-flow/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 root root
}
EOF

print_status "🎉 Production server setup completed!"
print_status "Next steps:"
echo "1. Upload your application files to /opt/trello-connect-flow"
echo "2. Edit .env.production with your production settings"
echo "3. Run: cd /opt/trello-connect-flow && ./deploy-production.sh"
echo "4. Your application will be available at https://boards.norgayhrconsulting.com.au"

print_status "Useful commands:"
echo "  - View nginx logs: tail -f /var/log/nginx/access.log"
echo "  - View application logs: docker compose -f docker-compose.unified.yml logs -f"
echo "  - Renew SSL: certbot renew"
echo "  - Restart nginx: systemctl restart nginx" 