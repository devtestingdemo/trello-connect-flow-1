from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from sqlalchemy.dialects.sqlite import JSON
from flask_login import UserMixin

# Create db instance (to be initialized with app in app.py)
db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    email = db.Column(db.String, primary_key=True)
    apiKey = db.Column(db.String, nullable=False)
    token = db.Column(db.String, nullable=False)
    linked_board_id = db.Column(db.String, nullable=True)  # Store the user's linked/created board ID
    linked_board_name = db.Column(db.String, nullable=True)  # Store the user's linked/created board name

    def get_id(self):
        return self.email

    def to_dict(self):
        return {
            'email': self.email,
            'apiKey': self.apiKey,
            'token': self.token,
            'linked_board_id': self.linked_board_id,
            'linked_board_name': self.linked_board_name
        }

class WebhookSetting(db.Model):
    __tablename__ = 'webhook_settings'
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String, db.ForeignKey('users.email'), nullable=False)
    board_id = db.Column(db.String, nullable=True)
    board_name = db.Column(db.String, nullable=True)
    event_type = db.Column(db.String, nullable=True)
    label = db.Column(db.String, nullable=True)  # Keep for backward compatibility
    label_id = db.Column(db.String, nullable=True)  # Store Trello label ID
    label_name = db.Column(db.String, nullable=True)  # Store Trello label name
    list_name = db.Column(db.String, nullable=True)
    webhook_id = db.Column(db.String, nullable=True)  # Trello webhook id

    def to_dict(self):
        return {
            'id': self.id,
            'user_email': self.user_email,
            'board_id': self.board_id,
            'board_name': self.board_name,
            'event_type': self.event_type,
            'label': self.label,  # Keep for backward compatibility
            'label_id': self.label_id,
            'label_name': self.label_name,
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

class TrelloWebhook(db.Model):
    __tablename__ = 'trello_webhooks'
    id = db.Column(db.Integer, primary_key=True)
    board_id = db.Column(db.String, unique=True, nullable=False)
    webhook_id = db.Column(db.String, nullable=False)
    callback_url = db.Column(db.String, nullable=False)
    date_created = db.Column(db.DateTime, server_default=db.func.now())
    settings = db.relationship('TrelloWebhookSetting', backref='trello_webhook', lazy=True)

class TrelloWebhookSetting(db.Model):
    __tablename__ = 'trello_webhook_settings'
    id = db.Column(db.Integer, primary_key=True)
    webhook_id = db.Column(db.String, db.ForeignKey('trello_webhooks.webhook_id'), nullable=False)
    event_type = db.Column(db.String, nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    extra_config = db.Column(JSON, nullable=True)
    __table_args__ = (db.UniqueConstraint('webhook_id', 'event_type', name='_webhook_event_uc'),)

# New consolidated model for user webhook preferences
class UserWebhookPreference(db.Model):
    __tablename__ = 'user_webhook_preferences'
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String, db.ForeignKey('users.email'), nullable=False)
    webhook_id = db.Column(db.String, nullable=False)  # Trello webhook id
    event_type = db.Column(db.String, nullable=False)
    board_id = db.Column(db.String, nullable=False)
    board_name = db.Column(db.String, nullable=False)
    label = db.Column(db.String, nullable=True)
    list_name = db.Column(db.String, nullable=True)
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    __table_args__ = (db.UniqueConstraint('user_email', 'webhook_id', 'event_type', name='_user_webhook_event_uc'),)

    def to_dict(self):
        return {
            'id': self.id,
            'user_email': self.user_email,
            'webhook_id': self.webhook_id,
            'event_type': self.event_type,
            'board_id': self.board_id,
            'board_name': self.board_name,
            'label': self.label,
            'list_name': self.list_name,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None
        } 