#!/bin/bash

# Generate nginx configuration with correct port from environment variables
set -e

# Load environment variables
if [ -f ".env.production" ]; then
    export $(grep -v '^#' .env.production | xargs)
else
    echo "Error: .env.production file not found"
    exit 1
fi

# Generate nginx config with correct port
cat > nginx.production.conf << EOF
server {
    listen 80;
    server_name boards.norgayhrconsulting.com.au www.boards.norgayhrconsulting.com.au;
    
    # Redirect HTTP to HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name boards.norgayhrconsulting.com.au www.boards.norgayhrconsulting.com.au;
    
    # SSL Configuration (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/boards.norgayhrconsulting.com.au/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/boards.norgayhrconsulting.com.au/privkey.pem;
    
    # SSL Security Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Proxy to Docker container
    location / {
        proxy_pass http://localhost:${FLASK_RUN_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;
}
EOF

echo "✅ Nginx configuration generated with port ${FLASK_RUN_PORT}" 