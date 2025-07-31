# backend/app_factory.py

from flask import Flask
from flask_cors import CORS
from db import db
from redis import Redis
from rq import Queue
from dotenv import load_dotenv
import os
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

def create_app():
    app = Flask(__name__)
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
    CORS(
        app,
        origins=["http://localhost:3000"],  # or your deployed frontend URL
        supports_credentials=True
    )
    db.init_app(app)
    with app.app_context():
        db.create_all()  # Ensures UserBoard and all tables are created
    return app, q