from flask import Flask, request, jsonify
from flask_cors import CORS
from db import db, User

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/api/users', methods=['POST'])
def add_user():
    data = request.json
    email = data.get('email')
    api_key = data.get('apiKey')
    token = data.get('token')
    if not email or not api_key or not token:
        return jsonify({'error': 'Missing required fields'}), 400
    user = User.query.get(email)
    if user:
        user.apiKey = api_key
        user.token = token
    else:
        user = User(email=email, apiKey=api_key, token=token)
        db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User added/updated', 'user': user.to_dict()}), 201

@app.route('/api/users/<path:email>', methods=['GET'])
def get_user(email):
    print(f"Looking up user: {email}")
    user = User.query.get(email)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user.to_dict()), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 