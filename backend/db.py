from flask_sqlalchemy import SQLAlchemy
from flask import Flask

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