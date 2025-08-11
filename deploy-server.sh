#!/bin/bash

# Server deployment script for Trello Connect Flow
set -e

echo "🚀 Starting server deployment of Trello Connect Flow..."

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

# Check if we're in the right directory
if [ ! -f "docker-compose.prod.yml" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Step 1: Check if .env.production exists
if [ ! -f ".env.production" ]; then
    print_warning ".env.production not found. Creating template..."
    cat > .env.production << EOF
FLASK_RUN_HOST=0.0.0.0
FLASK_RUN_PORT=4001
REDIS_PORT=6379
SECRET_KEY=spk-123
SQLALCHEMY_DATABASE_URI=sqlite:///instance/users.db
FRONTEND_URL=https://boards.norgayhrconsulting.com.au
FLASK_ENV=production
FLASK_DEBUG=0
FLASK_APP=app.py
EOF
    print_warning "Please edit .env.production with your actual values before continuing"
    exit 1
fi

# Step 2: Copy production env to backend for Docker build
print_status "Copying environment file to backend..."
cp .env.production backend/.env

# Step 3: Create instance directory with proper permissions
print_status "Setting up database directory..."
mkdir -p backend/instance
chmod 755 backend/instance

# Step 4: Stop existing containers and clean up orphans
print_status "Stopping existing containers and cleaning up orphans..."
docker compose -f docker-compose.prod.yml down --remove-orphans || true

# Force remove any conflicting containers
print_status "Removing any conflicting containers..."
docker rm -f boardsnorgayhrconsultingcomau-redis-1 2>/dev/null || true
docker rm -f boardsnorgayhrconsultingcomau-backend-1 2>/dev/null || true
docker rm -f boardsnorgayhrconsultingcomau-worker-1 2>/dev/null || true

# Step 5: Build and start containers
print_status "Building and starting containers..."
docker compose -f docker-compose.prod.yml up -d --build

# Step 6: Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 10

# Step 7: Check if services are running
print_status "Checking service status..."
if docker compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    print_status "✅ Services are running successfully!"
else
    print_error "❌ Some services failed to start. Check logs:"
    docker compose -f docker-compose.prod.yml logs
    exit 1
fi

# Step 8: Test API endpoint
print_status "Testing API endpoint..."
sleep 5  # Give the API a bit more time to start
if curl -s http://localhost:4001/api/users > /dev/null; then
    print_status "✅ API is responding correctly!"
else
    print_warning "⚠️  API might not be ready yet. Check logs:"
    docker compose -f docker-compose.prod.yml logs backend
    print_warning "Trying alternative port 5000..."
    if curl -s http://localhost:5000/api/users > /dev/null; then
        print_warning "⚠️  API is running on port 5000 instead of 4001"
    fi
fi

# Step 9: Copy frontend files to web directory
print_status "Copying frontend files to web directory..."
sudo cp -r frontend/dist/* /var/www/boards.norgayhrconsulting.com.au/
sudo chown -R www-data:www-data /var/www/boards.norgayhrconsulting.com.au
sudo chmod -R 755 /var/www/boards.norgayhrconsulting.com.au

print_status "🎉 Server deployment completed!"
print_status "Next steps:"
echo "1. Configure Apache virtual host (see DEPLOYMENT_GUIDE.md)"
echo "2. Set up SSL certificate with Let's Encrypt"
echo "3. Test your application at https://boards.norgayhrconsulting.com.au"

# Show running containers
echo ""
print_status "Running containers:"
docker compose -f docker-compose.prod.yml ps 