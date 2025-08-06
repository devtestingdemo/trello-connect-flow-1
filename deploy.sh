#!/bin/bash

# Configuration
APP_NAME="trello-connect-flow"
APP_DIR="/var/www/$APP_NAME"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"

echo "Starting deployment of $APP_NAME..."

# Create application directory
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

# Copy application files
echo "Copying application files..."
cp -r . $APP_DIR/

# Set up backend
echo "Setting up backend..."
cd $BACKEND_DIR

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOF
FLASK_ENV=production
FLASK_APP=app.py
FLASK_RUN_HOST=127.0.0.1
FLASK_RUN_PORT=5000
REDIS_PORT=6379
DATABASE_URL=sqlite:///instance/app.db
SECRET_KEY=$(openssl rand -hex 32)
EOF
fi

# Initialize database
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# Set up frontend
echo "Setting up frontend..."
cd $FRONTEND_DIR

# Install dependencies
npm install

# Build for production
npm run build

# Set proper permissions
echo "Setting permissions..."
sudo chown -R www-data:www-data $APP_DIR
sudo chmod -R 755 $APP_DIR

# Copy Apache configuration
echo "Setting up Apache..."
sudo cp $APP_DIR/apache-config.conf /etc/apache2/sites-available/$APP_NAME.conf
sudo a2ensite $APP_NAME
sudo a2dissite 000-default

# Copy systemd services
echo "Setting up systemd services..."
sudo cp $APP_DIR/trello-backend.service /etc/systemd/system/
sudo cp $APP_DIR/trello-worker.service /etc/systemd/system/

# Reload systemd and start services
sudo systemctl daemon-reload
sudo systemctl enable trello-backend
sudo systemctl enable trello-worker
sudo systemctl start trello-backend
sudo systemctl start trello-worker

# Restart Apache
sudo systemctl restart apache2

echo "Deployment completed!"
echo "Backend service status:"
sudo systemctl status trello-backend --no-pager
echo "Worker service status:"
sudo systemctl status trello-worker --no-pager
echo "Apache status:"
sudo systemctl status apache2 --no-pager 