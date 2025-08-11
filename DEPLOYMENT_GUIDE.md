# Deployment Guide for Trello Connect Flow

## Prerequisites
- Ubuntu/Debian server with Apache2 installed
- Docker and Docker Compose installed
- Domain name pointing to your server
- SSL certificate (Let's Encrypt recommended)

## Step 1: Prepare Your Application

### 1.1 Build Frontend
```bash
cd frontend
npm install
npm run build
```

### 1.2 Create Production Environment File
Create `.env.production` in the root directory:
```env
FLASK_RUN_HOST=0.0.0.0
FLASK_RUN_PORT=4001
REDIS_PORT=6379
SECRET_KEY=your-super-secret-production-key-here
SQLALCHEMY_DATABASE_URI=sqlite:///instance/users.db
FRONTEND_URL=https://boards.norgayhrconsulting.com.au
```

## Step 2: Set Up Server Directory Structure

```bash
# Create web directory
sudo mkdir -p /var/www/boards.norgayhrconsulting.com.au

# Copy built frontend files
sudo cp -r frontend/dist/* /var/www/boards.norgayhrconsulting.com.au/

# Set proper permissions
sudo chown -R www-data:www-data /var/www/boards.norgayhrconsulting.com.au
sudo chmod -R 755 /var/www/boards.norgayhrconsulting.com.au
```

## Step 3: Configure Apache Virtual Host

Create `/etc/apache2/sites-available/boards.norgayhrconsulting.com.au.conf`:

```apache
<IfModule mod_ssl.c>
<VirtualHost *:443>
    ServerName boards.norgayhrconsulting.com.au
    ServerAdmin webmaster@norgayhrconsulting.com.au
    DocumentRoot /var/www/boards.norgayhrconsulting.com.au
    
    # Serve static files
    <Directory /var/www/boards.norgayhrconsulting.com.au/>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>

    # API proxy
    ProxyPreserveHost On
    ProxyPass /api/ http://localhost:4001/api/
    ProxyPassReverse /api/ http://localhost:4001/api/

    RequestHeader set X-Forwarded-Proto "https"

    # Handle client-side routing
    RewriteEngine On
    RewriteCond %{REQUEST_URI} !^/api(/.*)?$
    RewriteCond %{REQUEST_FILENAME} !-f
    RewriteCond %{REQUEST_FILENAME} !-d
    RewriteCond %{REQUEST_URI} !\.(js|css|jpg|jpeg|png|gif|svg|ico|woff|woff2|ttf|eot|otf)$
    RewriteRule ^(.*)$ /index.html [QSA,L]
    
    ErrorLog ${APACHE_LOG_DIR}/boards_error.log
    CustomLog ${APACHE_LOG_DIR}/boards_access.log combined

    SSLCertificateFile /etc/letsencrypt/live/boards.norgayhrconsulting.com.au/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/boards.norgayhrconsulting.com.au/privkey.pem
    Include /etc/letsencrypt/options-ssl-apache.conf
</VirtualHost>
</IfModule>
```

## Step 4: Enable Required Apache Modules

```bash
sudo a2enmod ssl
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod rewrite
sudo a2enmod headers
sudo systemctl restart apache2
```

## Step 5: Set Up SSL Certificate (Let's Encrypt)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-apache

# Get SSL certificate
sudo certbot --apache -d boards.norgayhrconsulting.com.au

# Test auto-renewal
sudo certbot renew --dry-run
```

## Step 6: Deploy Backend with Docker

### 6.1 Update app_factory.py for Production
Update the CORS origins in `backend/app_factory.py`:
```python
CORS(
    app,
    origins=["https://boards.norgayhrconsulting.com.au"],
    supports_credentials=True
)
```

### 6.2 Create Production Docker Compose
Create `docker-compose.prod.yml`:
```yaml
version: '3.8'

services:
  redis:
    image: redis:7
    ports:
      - "6379:6379"
    restart: unless-stopped

  backend:
    build: ./backend
    command: flask run --host=0.0.0.0 --port=4001
    env_file:
      - .env.production
    ports:
      - "4001:4001"
    depends_on:
      - redis
    restart: unless-stopped
    volumes:
      - ./backend/instance:/app/instance

  worker:
    build: ./backend
    command: rq worker trello-events --url redis://redis:6379/0
    env_file:
      - .env.production
    depends_on:
      - redis
      - backend
    restart: unless-stopped
    volumes:
      - ./backend/instance:/app/instance
```

### 6.3 Deploy Backend
```bash
# Copy production env file
cp .env.production .env

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Check logs
docker-compose -f docker-compose.prod.yml logs -f
```

## Step 7: Enable Apache Site

```bash
# Enable the site
sudo a2ensite boards.norgayhrconsulting.com.au.conf

# Disable default site (optional)
sudo a2dissite 000-default.conf

# Test configuration
sudo apache2ctl configtest

# Restart Apache
sudo systemctl restart apache2
```

## Step 8: Test Your Deployment

1. **Frontend**: Visit `https://boards.norgayhrconsulting.com.au`
2. **API**: Test `https://boards.norgayhrconsulting.com.au/api/users`
3. **SSL**: Verify SSL certificate is working
4. **Logs**: Check Apache and Docker logs for errors

## Step 9: Monitoring and Maintenance

### Check Logs
```bash
# Apache logs
sudo tail -f /var/log/apache2/boards_error.log
sudo tail -f /var/log/apache2/boards_access.log

# Docker logs
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f worker
```

### Update Application
```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

### Backup Database
```bash
# Backup SQLite database
cp backend/instance/users.db backup/users_$(date +%Y%m%d_%H%M%S).db
```

## Troubleshooting

### Common Issues:
1. **CORS errors**: Check CORS origins in `app_factory.py`
2. **Database errors**: Ensure instance directory has write permissions
3. **SSL errors**: Verify certificate paths in Apache config
4. **Proxy errors**: Check if backend is running on port 4001

### Debug Commands:
```bash
# Check if backend is running
curl http://localhost:4001/api/users

# Check Apache configuration
sudo apache2ctl -S

# Check Docker containers
docker-compose -f docker-compose.prod.yml ps
``` 