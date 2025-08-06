#!/bin/bash

# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Apache and required modules
sudo apt install -y apache2 libapache2-mod-wsgi-py3

# Install Python and pip
sudo apt install -y python3 python3-pip python3-venv

# Install Redis
sudo apt install -y redis-server

# Install Node.js and npm (for building frontend)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Enable Apache modules
sudo a2enmod wsgi
sudo a2enmod rewrite
sudo a2enmod headers
sudo a2enmod proxy
sudo a2enmod proxy_http

# Restart Apache
sudo systemctl restart apache2
sudo systemctl enable apache2
sudo systemctl enable redis-server

echo "Server setup completed!" 