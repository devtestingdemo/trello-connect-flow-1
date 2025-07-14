from flask import Flask, request, jsonify
from flask_cors import CORS
from db import db, User, WebhookSetting, UserBoard
from redis import Redis
from rq import Queue
from tasks import process_trello_event
from dotenv import load_dotenv
import os
from app_factory import create_app
import requests
import json


load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
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
    # Remove webhook from Trello
    user = User.query.filter_by(email=setting.user_email).first()
    if user:
        trello_delete_url = f"https://api.trello.com/1/webhooks/{webhook_id}?key={user.apiKey}&token={user.token}"
        try:
            trello_resp = requests.delete(trello_delete_url)
            if trello_resp.status_code not in [200, 204]:
                print(f"Failed to delete Trello webhook: {trello_resp.text}")
        except Exception as e:
            print(f"Exception while deleting Trello webhook: {e}")
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

@app.route('/api/trello/verify', methods=['POST'])
def trello_verify():
    data = request.json
    api_key = data.get('apiKey')
    token = data.get('token')
    if not api_key or not token:
        return jsonify({'error': 'Missing apiKey or token'}), 400
    url = f'https://api.trello.com/1/members/me?key={api_key}&token={token}'
    resp = requests.get(url)
    if resp.status_code != 200:
        return jsonify({'error': 'Invalid API Key or Token', 'details': resp.text}), 401
    return jsonify(resp.json()), 200

@app.route('/api/trello/boards', methods=['POST'])
def trello_get_boards():
    data = request.json
    api_key = data.get('apiKey')
    token = data.get('token')
    if not api_key or not token:
        return jsonify({'error': 'Missing apiKey or token'}), 400
    boards_url = f'https://api.trello.com/1/members/me/boards?key={api_key}&token={token}'
    boards_resp = requests.get(boards_url)
    if boards_resp.status_code != 200:
        return jsonify({'error': 'Failed to fetch boards', 'details': boards_resp.text}), 400
    boards_data = boards_resp.json()
    # For each board, fetch its lists
    boards_with_lists = []
    for board in boards_data:
        lists_url = f'https://api.trello.com/1/boards/{board["id"]}/lists?key={api_key}&token={token}'
        lists_resp = requests.get(lists_url)
        lists_data = lists_resp.json() if lists_resp.status_code == 200 else []
        boards_with_lists.append({
            'id': board['id'],
            'name': board['name'],
            'lists': [l['name'] for l in lists_data]
        })
    return jsonify({'boards': boards_with_lists}), 200

@app.route('/api/trello/webhooks', methods=['POST'])
def trello_register_webhook():
    data = request.json
    api_key = data.get('apiKey')
    token = data.get('token')
    callback_url = data.get('callbackURL')
    id_model = data.get('idModel')
    description = data.get('description', '')
    if not api_key or not token or not callback_url or not id_model:
        return jsonify({'error': 'Missing required fields'}), 400

    # Check if a Trello webhook already exists for this token/model
    trello_webhooks_resp = requests.get(f'https://api.trello.com/1/tokens/{token}/webhooks?key={api_key}')
    if trello_webhooks_resp.status_code == 200:
        trello_webhooks = trello_webhooks_resp.json()
        existing = next((wh for wh in trello_webhooks if wh.get('idModel') == id_model and wh.get('callbackURL') == callback_url), None)
        if existing:
            # Webhook already exists, reuse it
            return jsonify(existing), 200

    # Otherwise, create a new Trello webhook
    url = f'https://api.trello.com/1/tokens/{token}/webhooks/'
    payload = {
        'key': api_key,
        'callbackURL': callback_url,
        'idModel': id_model,
        'description': description
    }
    resp = requests.post(url, json=payload)
    if resp.status_code not in [200, 201]:
        try:
            err = resp.json()
            msg = err.get('message', 'Failed to register webhook')
        except Exception:
            msg = resp.text
        return jsonify({'error': msg}), 400
    return jsonify(resp.json()), 201

@app.route('/api/trello/webhooks', methods=['GET'])
def trello_get_webhooks():
    api_key = request.args.get('apiKey')
    token = request.args.get('token')
    if not api_key or not token:
        return jsonify({'error': 'Missing apiKey or token'}), 400
    url = f'https://api.trello.com/1/tokens/{token}/webhooks?key={api_key}'
    resp = requests.get(url)
    if resp.status_code != 200:
        try:
            err = resp.json()
            msg = err.get('message', 'Failed to fetch webhooks')
        except Exception:
            msg = resp.text
        return jsonify({'error': msg}), 400
    return jsonify(resp.json()), 200


if __name__ == '__main__':
    host = os.getenv('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_RUN_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1', 'yes']
    app.run(host=host, port=port, debug=debug)