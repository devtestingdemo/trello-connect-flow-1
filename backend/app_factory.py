# backend/app_factory.py

from flask import Flask
from flask_cors import CORS
from db import db
from redis import Redis
from rq import Queue
import os

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///users.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    redis_url = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
    redis_conn = Redis.from_url(redis_url)
    q = Queue('trello-events', connection=redis_conn)
    CORS(app)
    db.init_app(app)
    with app.app_context():
        db.create_all()  # Ensures UserBoard and all tables are created
    return app, q