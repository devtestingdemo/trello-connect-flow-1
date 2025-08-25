# backend/app_factory.py

from flask import Flask, send_from_directory
from flask_cors import CORS
from db import db
from redis import Redis
from rq import Queue
from dotenv import load_dotenv
import os
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

def create_app():
    app = Flask(__name__, static_folder='frontend/dist', static_url_path='')
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-very-secret-key-here')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///users.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    redis_port = os.environ.get('REDIS_PORT', '6379')
    redis_url = f"redis://redis:{redis_port}/0"
    redis_conn = Redis.from_url(redis_url)
    q = Queue('trello-events', connection=redis_conn)
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
        if path.startswith('api/'):
            # Let Flask handle API routes
            return app.send_static_file('index.html')
        if path and os.path.exists(os.path.join(app.static_folder, path)):
            # Serve static files
            return send_from_directory(app.static_folder, path)
        else:
            # Serve index.html for React Router routes
            return send_from_directory(app.static_folder, 'index.html')
    
    return app, q