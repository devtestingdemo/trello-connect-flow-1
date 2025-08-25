#!/bin/bash

# Local development deployment script for Trello Connect Flow
set -e

echo "🚀 Starting local deployment of Trello Connect Flow..."

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
if [ ! -f "docker-compose.yml" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Step 1: Check if .env exists, create if not
if [ ! -f ".env" ]; then
    print_warning ".env not found. Creating local development environment file..."
    cat > .env << EOF
FLASK_RUN_HOST=0.0.0.0
FLASK_RUN_PORT=5000
REDIS_PORT=6379
SECRET_KEY=dev-secret-key-change-in-production
SQLALCHEMY_DATABASE_URI=sqlite:///instance/users.db
FRONTEND_URL=http://localhost:3000
FLASK_ENV=development
FLASK_DEBUG=1
FLASK_APP=app.py
EOF
    print_status "Created .env file with local development settings"
fi

# Step 2: Copy env to backend for Docker build
print_status "Copying environment file to backend..."
cp .env backend/.env

# Step 3: Create instance directory with proper permissions
print_status "Setting up database directory..."
mkdir -p backend/instance
chmod 755 backend/instance

# Step 4: Initialize database
print_status "Initializing database..."
cd backend
python3 -c "
from app_factory import create_app
from db import db
app, q = create_app()
with app.app_context():
    db.create_all()
    print('Database initialized successfully')
"
cd ..

# Step 5: Stop existing containers and clean up orphans
print_status "Stopping existing containers and cleaning up orphans..."
docker compose down --remove-orphans || true

# Step 6: Build and start containers
print_status "Building and starting containers..."
docker compose up -d --build

# Step 7: Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 15

# Step 8: Check if services are running
print_status "Checking service status..."
if docker compose ps | grep -q "Up"; then
    print_status "✅ Services are running successfully!"
else
    print_error "❌ Some services failed to start. Check logs:"
    docker compose logs
    exit 1
fi

# Step 9: Test API endpoint
print_status "Testing API endpoint..."
sleep 5  # Give the API a bit more time to start
if curl -s http://localhost:5000/api/users > /dev/null; then
    print_status "✅ API is responding correctly!"
else
    print_warning "⚠️  API might not be ready yet. Check logs:"
    docker compose logs backend
fi

# Step 10: Test frontend
print_status "Testing frontend..."
sleep 3
if curl -s http://localhost:3000 > /dev/null; then
    print_status "✅ Frontend is responding correctly!"
else
    print_warning "⚠️  Frontend might not be ready yet. Check logs:"
    docker compose logs frontend
fi

print_status "🎉 Local deployment completed!"
print_status "Your application is now running at:"
echo "  - Frontend: http://localhost:3000"
echo "  - Backend API: http://localhost:5000"
echo "  - Redis: localhost:6379"

print_status "Useful commands:"
echo "  - View logs: docker compose logs -f"
echo "  - Stop services: docker compose down"
echo "  - Restart services: docker compose restart"
echo "  - Rebuild and restart: docker compose up -d --build"

# Show running containers
echo ""
print_status "Running containers:"
docker compose ps 