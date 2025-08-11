#!/bin/bash

# Script to copy updated files to server
# Usage: ./copy-to-server.sh

echo "📁 Copying updated files to server..."

# Files that were updated
FILES_TO_COPY=(
    "backend/Dockerfile"
    "docker-compose.prod.yml"
    "deploy.sh"
    "DEPLOYMENT_GUIDE.md"
    ".env.production"
    "frontend/dist/"
)

echo "Files to copy:"
for file in "${FILES_TO_COPY[@]}"; do
    echo "  - $file"
done

echo ""
echo "To copy these files to your server, run:"
echo ""
echo "scp -r ${FILES_TO_COPY[@]} ubuntu@vps-a404fece:/var/www/boards.norgayhrconsulting.com.au/"
echo ""
echo "Or copy the entire project:"
echo "scp -r . ubuntu@vps-a404fece:/var/www/boards.norgayhrconsulting.com.au/"
echo ""
echo "Then SSH to your server and run:"
echo "cd /var/www/boards.norgayhrconsulting.com.au"
echo "./deploy.sh" 