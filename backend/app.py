from flask import Flask, request, jsonify
from flask_cors import CORS
from db import db, User, WebhookSetting, UserBoard
from redis import Redis
from rq import Queue
from tasks import process_trello_event
import os
from app_factory import create_app
import requests
import json
app, q = create_app()


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

@app.route('/api/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([u.to_dict() for u in users]), 200

@app.route('/api/webhook-settings', methods=['POST'])
def save_webhook_setting():
    data = request.json
    user_email = data.get('user_email')
    board_id = data.get('board_id')
    board_name = data.get('board_name')
    event_type = data.get('event_type')
    label = data.get('label')
    list_name = data.get('list_name')
    webhook_id = data.get('webhook_id')
    if not user_email or not webhook_id:
        return jsonify({'error': 'Missing required fields'}), 400
    setting = WebhookSetting(
        user_email=user_email,
        board_id=board_id,
        board_name=board_name,
        event_type=event_type,
        label=label,
        list_name=list_name,
        webhook_id=webhook_id
    )
    db.session.add(setting)
    db.session.commit()
    return jsonify({'message': 'Webhook setting saved', 'setting': setting.to_dict()}), 201

@app.route('/api/webhook-settings/<webhook_id>', methods=['DELETE'])
def delete_webhook_setting(webhook_id):
    setting = WebhookSetting.query.filter_by(webhook_id=webhook_id).first()
    if not setting:
        return jsonify({'error': 'Webhook setting not found'}), 404
    db.session.delete(setting)
    db.session.commit()
    return jsonify({'message': 'Webhook setting deleted'}), 200

@app.route('/api/webhook-settings', methods=['GET'])
def get_webhook_settings():
    settings = WebhookSetting.query.all()
    return jsonify([s.to_dict() for s in settings]), 200

@app.route('/api/trello-webhook', methods=['GET', 'POST'])
def trello_webhook():
    try:
        print(f"trello_webhook ::")
        if request.method in ['GET', 'HEAD']:
            return '', 200
        if request.method == 'POST':
            if not request.is_json:
                return jsonify({'error': 'Content-Type must be application/json'}), 415
            payload = request.get_json(silent=True)
            #print("trello_webhook :: payload ::",payload)
            if not payload:
                return jsonify({'success': True}), 200
            if 'action' not in payload:
                return jsonify({'error': 'Invalid webhook payload'}), 400
            event_type = payload['action'].get('type')
            print(f"trello_webhook :: event_type :: {event_type}")

            # --- NEW CODE STARTS HERE ---
            webhook_id = payload.get('webhook', {}).get('id')
            if not webhook_id:
                return jsonify({'error': 'Missing webhook_id'}), 400

            setting = WebhookSetting.query.filter_by(webhook_id=webhook_id).first()
            #print(f"trello_webhook :: {setting.__annotations__}")
            if not setting:
                return jsonify({'error': 'Invalid webhook_id'}), 404

            # Get all event_types for this user and webhook
            allowed_event_types = [
                "commentCard" if s.event_type == "Mentioned in a card" else (
                    "addMemberToCard" if s.event_type == "Added to a card" else s.event_type
                )
                for s in WebhookSetting.query.filter_by(
                    user_email=setting.user_email,
                    webhook_id=webhook_id
                ).all()
            ]
            print(f"Allowed event types for webhook {webhook_id}: {allowed_event_types}")
            # --- NEW CODE ENDS HERE ---

            if event_type not in allowed_event_types:
                return jsonify({'status': 'ignored', 'reason': f'Event type {event_type} not handled'}), 200

            if event_type == "commentCard":
                # Fetch the user
                user = User.query.filter_by(email=setting.user_email).first()
                trello_username = None
                if user:
                    import requests
                    url = f"https://api.trello.com/1/members/me?key={user.apiKey}&token={user.token}"
                    try:
                        resp = requests.get(url)
                        if resp.status_code == 200:
                            trello_username = resp.json().get("username")
                    except Exception as e:
                        print(f"Error fetching Trello username: {e}")
                comment_text = payload.get('action', {}).get('data', {}).get('text', '')
                if not trello_username or f"@{trello_username}" not in comment_text:
                    print("User not mentioned in comment, skipping queue.")
                    return jsonify({'status': 'ignored', 'reason': 'User not mentioned in comment'}), 200

            q.enqueue(process_trello_event, payload)
            return jsonify({'status': 'queued', 'event_type': event_type}), 200
    except Exception as e:
        print(f"trello_webhook :: {e}");
        return jsonify({'status': 'failed', 'error': str(e)});

@app.route('/api/trello/setup-board', methods=['POST'])
def setup_trello_board():
    data = request.json
    email = data.get('email')
    api_key = data.get('apiKey')
    token = data.get('token')
    # Use username from email as board name
    board_name = email.split('@')[0] if email and '@' in email else 'Integration Board'
    if not email or not api_key or not token:
        return jsonify({'error': 'Missing required fields'}), 400
    # Check if board already exists for user
    user_board = UserBoard.query.filter_by(user_email=email).first()
    if user_board:
        return jsonify({'message': 'Board already exists', 'board': user_board.to_dict()}), 200
    # Create board via Trello API
    board_res = requests.post(
        f'https://api.trello.com/1/boards/',
        params={'name': board_name, 'defaultLists': 'false', 'key': api_key, 'token': token}
    )
    if board_res.status_code != 200:
        return jsonify({'error': 'Failed to create board', 'details': board_res.text}), 500
    board = board_res.json()
    board_id = board['id']
    # Create required lists
    list_names = ['Enquiry In', 'Todo', 'Doing', 'Done']
    lists = {}
    for name in list_names:
        list_res = requests.post(
            f'https://api.trello.com/1/lists',
            params={'name': name, 'idBoard': board_id, 'key': api_key, 'token': token}
        )
        if list_res.status_code != 200:
            return jsonify({'error': f'Failed to create list {name}', 'details': list_res.text}), 500
        list_data = list_res.json()
        lists[name] = list_data['id']
    # Save to DB
    user_board = UserBoard(user_email=email, board_id=board_id, board_name=board_name, lists=lists)
    db.session.add(user_board)
    db.session.commit()
    return jsonify({'message': 'Board created', 'board': user_board.to_dict()}), 201


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 