# Production Deployment Guide

This guide will help you deploy the Trello Connect Flow application to a production server.

## Prerequisites

- A Ubuntu/Debian server with SSH access
- A domain name pointing to your server (e.g., `boards.norgayhrconsulting.com.au`)
- Root access or sudo privileges

## Step 1: Server Setup

### 1.1 Connect to your server
```bash
ssh user@your-server-ip
```

### 1.2 Upload the application files
```bash
# From your local machine
scp -r trello-connect-flow/ user@your-server-ip:/tmp/
```

### 1.3 Run the server setup script
```bash
# On the server
sudo mv /tmp/trello-connect-flow /opt/
cd /opt/trello-connect-flow
sudo chmod +x setup-production.sh
sudo ./setup-production.sh
```

This script will:
- Update system packages
- Install Docker, Docker Compose, nginx, and certbot
- Configure firewall
- Set up nginx reverse proxy
- Install SSL certificate with Let's Encrypt
- Set up automatic SSL renewal

## Step 2: Configure Production Environment

### 2.1 Edit production environment file
```bash
nano .env.production
```

Update the following values:
```env
FLASK_RUN_HOST=0.0.0.0
FLASK_RUN_PORT=5000
REDIS_PORT=6379
SECRET_KEY=your-super-secure-random-secret-key-here
SQLALCHEMY_DATABASE_URI=sqlite:///instance/users.db
FRONTEND_URL=https://boards.norgayhrconsulting.com.au
FLASK_ENV=production
FLASK_DEBUG=0
FLASK_APP=app.py
```

**Important:** Generate a secure SECRET_KEY:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2.2 Make deployment script executable
```bash
chmod +x deploy-production.sh
```

## Step 3: Deploy the Application

### 3.1 Run the production deployment
```bash
./deploy-production.sh
```

This will:
- Build the frontend for production
- Set up the database
- Build and start Docker containers
- Test the application

### 3.2 Verify the deployment
```bash
# Check if containers are running
docker compose -f docker-compose.unified.yml ps

# Test the application
curl -I https://boards.norgayhrconsulting.com.au
```

## Step 4: Post-Deployment

### 4.1 Set up monitoring (optional)
```bash
# View application logs
docker compose -f docker-compose.unified.yml logs -f

# View nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### 4.2 Set up backups (recommended)
```bash
# Create backup script
cat > /opt/backup-trello-app.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups/trello-connect-flow"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup database
docker compose -f /opt/trello-connect-flow/docker-compose.unified.yml exec -T backend sqlite3 /app/instance/users.db ".backup '/tmp/users_backup.db'"
docker cp trello-connect-flow-backend-1:/tmp/users_backup.db $BACKUP_DIR/users_$DATE.db

# Backup environment files
cp /opt/trello-connect-flow/.env.production $BACKUP_DIR/env_$DATE.production

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
find $BACKUP_DIR -name "*.production" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR"
EOF

chmod +x /opt/backup-trello-app.sh

# Add to crontab for daily backups
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/backup-trello-app.sh") | crontab -
```

## Step 5: Maintenance

### 5.1 Update the application
```bash
# Pull latest changes
git pull origin main

# Rebuild and redeploy
./deploy-production.sh
```

### 5.2 Monitor SSL certificate
```bash
# Check SSL certificate status
certbot certificates

# Manually renew if needed
certbot renew
```

### 5.3 Restart services if needed
```bash
# Restart application
docker compose -f docker-compose.unified.yml restart

# Restart nginx
sudo systemctl restart nginx
```

## Troubleshooting

### Application not accessible
```bash
# Check if containers are running
docker compose -f docker-compose.unified.yml ps

# Check application logs
docker compose -f docker-compose.unified.yml logs backend

# Check nginx status
sudo systemctl status nginx

# Check firewall
sudo ufw status
```

### SSL certificate issues
```bash
# Check certificate status
certbot certificates

# Renew certificate
certbot renew

# Check nginx configuration
sudo nginx -t
```

### Database issues
```bash
# Access database
docker compose -f docker-compose.unified.yml exec backend sqlite3 /app/instance/users.db

# Backup database
docker compose -f docker-compose.unified.yml exec backend sqlite3 /app/instance/users.db ".backup '/tmp/backup.db'"
```

## Security Considerations

1. **Firewall**: Only ports 22 (SSH), 80 (HTTP), and 443 (HTTPS) should be open
2. **SSL**: Always use HTTPS in production
3. **Secrets**: Use strong, unique SECRET_KEY
4. **Updates**: Keep system packages and Docker images updated
5. **Backups**: Regular backups of database and configuration files
6. **Monitoring**: Set up log monitoring and alerting

## Performance Optimization

1. **Nginx caching**: Static assets are automatically cached
2. **Gzip compression**: Enabled in nginx configuration
3. **Database**: Consider using PostgreSQL for better performance
4. **Redis**: Already configured for background tasks
5. **CDN**: Consider using a CDN for static assets

## Support

If you encounter issues:
1. Check the logs: `docker compose -f docker-compose.unified.yml logs -f`
2. Verify configuration files
3. Check system resources: `htop`, `df -h`, `free -h`
4. Review this guide for common solutions 