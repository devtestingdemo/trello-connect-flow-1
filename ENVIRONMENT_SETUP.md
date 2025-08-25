# Environment Variables Setup Guide

This guide explains how environment variables are configured in the production deployment.

## Environment Variables in `.env.production`

Your `.env.production` file contains:

```env
FLASK_RUN_HOST=0.0.0.0
FLASK_RUN_PORT=5000
REDIS_PORT=6379
SECRET_KEY=spk-123
SQLALCHEMY_DATABASE_URI=sqlite:///instance/users.db
FRONTEND_URL=https://boards.norgayhrconsulting.com.au
FLASK_ENV=production
FLASK_DEBUG=0
FLASK_APP=app.py
```

## How Environment Variables Are Used

### 1. **Docker Compose (`docker-compose.prod.yml`)**

The production Docker Compose file uses environment variables in two ways:

#### **env_file directive:**
```yaml
env_file:
  - .env.production
```

#### **Explicit environment variables:**
```yaml
environment:
  - FLASK_RUN_HOST=${FLASK_RUN_HOST}
  - FLASK_RUN_PORT=${FLASK_RUN_PORT}
  - REDIS_PORT=${REDIS_PORT}
  - SECRET_KEY=${SECRET_KEY}
  - SQLALCHEMY_DATABASE_URI=${SQLALCHEMY_DATABASE_URI}
  - FRONTEND_URL=${FRONTEND_URL}
  - FLASK_ENV=${FLASK_ENV}
  - FLASK_DEBUG=${FLASK_DEBUG}
  - FLASK_APP=${FLASK_APP}
```

### 2. **Deployment Script (`deploy-production.sh`)**

The deployment script:

1. **Loads environment variables:**
   ```bash
   export $(grep -v '^#' .env.production | xargs)
   ```

2. **Uses them in commands:**
   ```bash
   # Dynamic port checking
   docker ps -a --filter "publish=${FLASK_RUN_PORT}" --format "{{.Names}}" | xargs -r docker rm -f
   
   # Dynamic URL testing
   curl -s http://localhost:${FLASK_RUN_PORT}/api/users
   ```

3. **Copies to multiple locations:**
   ```bash
   cp .env.production backend/.env
   cp .env.production .env
   ```

### 3. **Nginx Configuration (`generate-nginx-config.sh`)**

The nginx config generator:

1. **Loads environment variables:**
   ```bash
   export $(grep -v '^#' .env.production | xargs)
   ```

2. **Generates config with correct port:**
   ```nginx
   proxy_pass http://localhost:${FLASK_RUN_PORT};
   ```

## Environment Variable Flow

```
.env.production
    ↓
deploy-production.sh (loads & exports)
    ↓
docker-compose.prod.yml (uses in containers)
    ↓
Docker containers (receive as env vars)
    ↓
Flask application (uses for configuration)
```

## Key Environment Variables Explained

| Variable | Purpose | Example |
|----------|---------|---------|
| `FLASK_RUN_HOST` | Flask server host | `0.0.0.0` |
| `FLASK_RUN_PORT` | Flask server port | `5000` |
| `REDIS_PORT` | Redis server port | `6379` |
| `SECRET_KEY` | Flask secret key | `your-secret-key` |
| `SQLALCHEMY_DATABASE_URI` | Database connection | `sqlite:///instance/users.db` |
| `FRONTEND_URL` | Frontend URL for CORS | `https://boards.norgayhrconsulting.com.au` |
| `FLASK_ENV` | Flask environment | `production` |
| `FLASK_DEBUG` | Debug mode | `0` (off) |
| `FLASK_APP` | Flask app entry point | `app.py` |

## Security Considerations

1. **SECRET_KEY**: Should be a strong, random string
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Database URI**: Use secure database in production
   ```env
   SQLALCHEMY_DATABASE_URI=postgresql://user:pass@localhost/dbname
   ```

3. **Environment**: Always use `production` for production
   ```env
   FLASK_ENV=production
   FLASK_DEBUG=0
   ```

## Testing Environment Variables

You can test if environment variables are loaded correctly:

```bash
# Check if variables are exported
echo $FLASK_RUN_PORT

# Test Docker Compose variable substitution
docker compose -f docker-compose.prod.yml config

# Check what environment variables containers receive
docker compose -f docker-compose.prod.yml exec backend env | grep FLASK
```

## Troubleshooting

### Environment variables not loading:
```bash
# Check if .env.production exists
ls -la .env.production

# Check file format (no spaces around =)
cat .env.production

# Test loading manually
export $(grep -v '^#' .env.production | xargs)
echo $FLASK_RUN_PORT
```

### Docker containers not receiving variables:
```bash
# Check Docker Compose config
docker compose -f docker-compose.prod.yml config

# Check container environment
docker compose -f docker-compose.prod.yml exec backend env
```

### Nginx proxy not working:
```bash
# Check generated nginx config
cat nginx.production.conf

# Test nginx configuration
sudo nginx -t

# Check nginx logs
sudo tail -f /var/log/nginx/error.log
``` 