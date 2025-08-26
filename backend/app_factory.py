# backend/app_factory.py

from flask import Flask, send_from_directory, abort
from flask_cors import CORS
from db import db
from redis import Redis
from rq import Queue
from dotenv import load_dotenv
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

def create_app():
    app = Flask(__name__, static_folder='frontend/dist', static_url_path='')
    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        raise ValueError("SECRET_KEY environment variable must be set")
    app.config['SECRET_KEY'] = secret_key
    # Use environment variable directly for database URI
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:////app/instance/users.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # Redis connection - will be established when needed
    redis_port = os.environ.get('REDIS_PORT', '6379')
    redis_url = f"redis://redis:{redis_port}/0"
    
    # Create Redis connection with error handling
    try:
        redis_conn = Redis.from_url(redis_url, socket_connect_timeout=5, socket_timeout=5)
        q = Queue('trello-events', connection=redis_conn)
    except Exception as e:
        # If Redis is not available, create a dummy queue
        logger.warning(f"Redis connection failed: {e}. Using dummy queue.")
        redis_conn = None
        q = None
    app.config['SESSION_COOKIE_SAMESITE'] = 'None'
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_DOMAIN'] = None  # Allow cross-subdomain cookies
    # Get frontend URL from environment or use default
    frontend_url = os.environ.get('FRONTEND_URL', 'https://boards.norgayhrconsulting.com.au')
    
    CORS(
        app,
        origins=[frontend_url, "http://localhost:3000", "http://localhost:5000"],  # Allow both production and development
        supports_credentials=True
    )
    db.init_app(app)
    
    # Serve React app for any non-API route
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        # Skip API routes - let Flask handle them
        if path.startswith('api/'):
            return None  # This will let Flask continue to the next route handler
        
        # Check if the requested path exists as a static file
        static_file_path = os.path.join(app.static_folder, path)
        if path and os.path.exists(static_file_path) and os.path.isfile(static_file_path):
            # Serve static files (CSS, JS, images, etc.)
            return send_from_directory(app.static_folder, path)
        else:
            # Serve index.html for React Router routes
            return send_from_directory(app.static_folder, 'index.html')
    
    # Proxy Google OAuth script if needed (MUST come after catch-all route)
    @app.route('/google-oauth.js')
    def proxy_google_oauth():
        import requests
        try:
            response = requests.get('https://accounts.google.com/gsi/client', timeout=10)
            return response.content, response.status_code, {'Content-Type': 'application/javascript'}
        except Exception as e:
            logger.error(f"Failed to proxy Google OAuth script: {e}")
            return "console.error('Google OAuth script failed to load');", 500, {'Content-Type': 'application/javascript'}
    
    return app, q