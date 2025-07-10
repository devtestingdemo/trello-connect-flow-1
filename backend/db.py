from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from sqlalchemy.dialects.sqlite import JSON

# Create db instance (to be initialized with app in app.py)
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    email = db.Column(db.String, primary_key=True)
    apiKey = db.Column(db.String, nullable=False)
    token = db.Column(db.String, nullable=False)

    def to_dict(self):
        return {
            'email': self.email,
            'apiKey': self.apiKey,
            'token': self.token
        }

class WebhookSetting(db.Model):
    __tablename__ = 'webhook_settings'
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String, db.ForeignKey('users.email'), nullable=False)
    board_id = db.Column(db.String, nullable=True)
    board_name = db.Column(db.String, nullable=True)
    event_type = db.Column(db.String, nullable=True)
    label = db.Column(db.String, nullable=True)
    list_name = db.Column(db.String, nullable=True)
    webhook_id = db.Column(db.String, nullable=True)  # Trello webhook id

    def to_dict(self):
        return {
            'id': self.id,
            'user_email': self.user_email,
            'board_id': self.board_id,
            'board_name': self.board_name,
            'event_type': self.event_type,
            'label': self.label,
            'list_name': self.list_name,
            'webhook_id': self.webhook_id
        }

class UserBoard(db.Model):
    __tablename__ = 'user_boards'
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String, db.ForeignKey('users.email'), nullable=False)
    board_id = db.Column(db.String, nullable=False)
    board_name = db.Column(db.String, nullable=False)
    lists = db.Column(JSON, nullable=False)  # {list_name: list_id}

    def to_dict(self):
        return {
            'id': self.id,
            'user_email': self.user_email,
            'board_id': self.board_id,
            'board_name': self.board_name,
            'lists': self.lists
        } 