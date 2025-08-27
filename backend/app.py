from flask import Flask, request, jsonify
from flask_cors import CORS
from db import db, User, WebhookSetting, UserBoard, TrelloWebhook, TrelloWebhookSetting
from redis import Redis
from rq import Queue
from tasks import process_trello_event
from dotenv import load_dotenv
import os
import time
import logging
from app_factory import create_app
import requests
import json
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

app, q = create_app()
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Database initialization function - will be called when needed
def init_db():
    with app.app_context():
        try:
            # Check if database already exists and has tables
            try:
                from sqlalchemy import text
                db.session.execute(text('SELECT 1 FROM users LIMIT 1'))
                logger.info("Database already exists and has tables")
                return
            except Exception:
                # Database or tables don't exist, create them
                pass

            # Create instance directory if it doesn't exist
            import os
            instance_path = os.path.join(os.path.dirname(__file__), 'instance')
            os.makedirs(instance_path, exist_ok=True)

            db.create_all()
            logger.info("Database tables initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            # Log more details about the error
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            # Don't crash the app, just log the error
            pass

# Initialize database when app starts
init_db()

# Remove UserLogin class, use User directly
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/api/login', methods=['POST'])
def login():
    # Ensure database is initialized
    try:
        init_db()
    except Exception as e:
        logger.error(f"Database initialization failed during login: {e}")
        return jsonify({'error': 'Database initialization failed'}), 500
    
    data = request.json
    email = data.get('email')
    user = User.query.get(email)
    if not user:
        user = User(email=email, apiKey='', token='')  # Empty Trello fields
        db.session.add(user)
        db.session.commit()
    login_user(user)
    return jsonify({'message': 'Logged in', 'email': user.email}), 200

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out'}), 200



@app.route('/api/users/trello', methods=['POST'])
@login_required
def link_trello():

    data = request.json
    api_key = data.get('apiKey')
    token = data.get('token')
    user = current_user
    if not api_key or not token:
        return jsonify({'error': 'Missing Trello API key or token'}), 400
    user.apiKey = api_key
    user.token = token
    db.session.commit()
    return jsonify({'message': 'Trello account linked'}), 200


def upsert_trello_webhook_setting(webhook_id, event_type, enabled=True, extra_config=None):
    tws = TrelloWebhookSetting.query.filter_by(webhook_id=webhook_id, event_type=event_type).first()
    if tws:
        tws.enabled = enabled
        tws.extra_config = extra_config
    else:
        tws = TrelloWebhookSetting(webhook_id=webhook_id, event_type=event_type, enabled=enabled, extra_config=extra_config)
        db.session.add(tws)
    db.session.commit()
    return tws


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
    logger.info(f"Looking up user: {email}")
    user = User.query.get(email)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user.to_dict()), 200

@app.route('/api/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([u.to_dict() for u in users]), 200

@app.route('/api/webhook-settings', methods=['POST'])
@login_required
def save_webhook_setting():
    data = request.json
    board_id = data.get('board_id')
    board_name = data.get('board_name')
    event_type = data.get('event_type')
    # Legacy name-only
    label = data.get('label')
    # Preferred fields
    label_id = data.get('label_id')
    label_name = data.get('label_name') or label
    list_name = data.get('list_name')
    webhook_id = data.get('webhook_id')
    if not webhook_id:
        return jsonify({'error': 'Missing required fields'}), 400

    # If a label_id is provided, validate it belongs to the user's linked board
    if label_id:
        user_board = UserBoard.query.filter_by(user_email=current_user.email).first()
        target_board_id = user_board.board_id if user_board else board_id
        if not target_board_id:
            return jsonify({'error': 'No linked board to validate label against'}), 400
        api_key = current_user.apiKey
        token = current_user.token
        try:
            labels_url = f'https://api.trello.com/1/boards/{target_board_id}/labels?key={api_key}&token={token}'
            labels_resp = requests.get(labels_url)
            if labels_resp.status_code != 200:
                return jsonify({'error': 'Failed to fetch board labels for validation', 'details': labels_resp.text}), 400
            labels = labels_resp.json()
            if not any(l.get('id') == label_id for l in labels):
                return jsonify({'error': 'Selected label does not belong to the linked board'}), 400
        except Exception as e:
            logger.error(f'Label validation failed: {e}')
            return jsonify({'error': 'Label validation failed'}), 400

    setting = WebhookSetting(
        user_email=current_user.email,
        board_id=board_id,
        board_name=board_name,
        event_type=event_type,
        label=label_name,
        label_id=label_id,
        label_name=label_name,
        list_name=list_name,
        webhook_id=webhook_id
    )
    db.session.add(setting)
    db.session.commit()
    return jsonify({'message': 'Webhook setting saved', 'setting': setting.to_dict()}), 201

@app.route('/api/webhook-settings/<setting_id>', methods=['DELETE'])
@login_required
def delete_webhook_setting(setting_id):
    # First try to find by setting ID (for individual event deletion)
    setting = WebhookSetting.query.filter_by(id=setting_id, user_email=current_user.email).first()
    
    if not setting:
        # If not found by ID, try by webhook_id (for webhook-level deletion)
        setting = WebhookSetting.query.filter_by(webhook_id=setting_id, user_email=current_user.email).first()
    
    if setting:
        webhook_id = setting.webhook_id
        db.session.delete(setting)
        db.session.commit()
        
        # Check if this was the last setting for this webhook
        remaining_settings = WebhookSetting.query.filter_by(webhook_id=webhook_id).count()
        if remaining_settings == 0:
            # Delete the Trello webhook if no more settings exist
            pass  # No action needed when no settings remain
        if current_user.apiKey and current_user.token:
            trello_delete_url = f"https://api.trello.com/1/webhooks/{webhook_id}?key={current_user.apiKey}&token={current_user.token}"
            try:
                trello_resp = requests.delete(trello_delete_url)
                if trello_resp.status_code not in [200, 204]:
                    logger.warning(f"Failed to delete Trello webhook: {trello_resp.text}")
                else:
                    logger.info(f"Successfully deleted Trello webhook: {webhook_id}")
            except Exception as e:
                logger.error(f"Exception while deleting Trello webhook: {e}")
    
    return jsonify({'message': 'Webhook setting deleted'}), 200

@app.route('/api/test-worker', methods=['POST'])
def test_worker():
    """Test endpoint to verify worker is processing tasks"""
    def test_task():
        logger.info("[Worker] Test task executed successfully!")
        return "Test completed"
    
    job = q.enqueue(test_task)
    logger.info(f"Test task queued with job ID: {job.id}")
    return jsonify({'message': 'Test task queued', 'job_id': job.id}), 200

@app.route('/api/debug/webhooks', methods=['GET'])
def debug_webhooks():
    """Debug endpoint to check webhook settings in database"""
    trello_webhooks = TrelloWebhook.query.all()
    trello_webhook_settings = TrelloWebhookSetting.query.all()
    webhook_settings = WebhookSetting.query.all()
    
    return jsonify({
        'trello_webhooks': [{'board_id': w.board_id, 'webhook_id': w.webhook_id} for w in trello_webhooks],
        'trello_webhook_settings': [{'webhook_id': s.webhook_id, 'event_type': s.event_type, 'enabled': s.enabled} for s in trello_webhook_settings],
        'webhook_settings': [{'webhook_id': s.webhook_id, 'event_type': s.event_type, 'user_email': s.user_email} for s in webhook_settings]
    }), 200

@app.route('/api/fix-webhook-settings', methods=['POST'])
def fix_webhook_settings():
    """Fix missing TrelloWebhookSetting records for existing webhooks"""
    try:
        # Get all webhook settings that don't have corresponding TrelloWebhookSetting records
        webhook_settings = WebhookSetting.query.all()
        created_count = 0
        
        for ws in webhook_settings:
            # Check if TrelloWebhookSetting already exists
            existing = TrelloWebhookSetting.query.filter_by(
                webhook_id=ws.webhook_id, 
                event_type=ws.event_type
            ).first()
            
            if not existing:
                # Create missing TrelloWebhookSetting
                tws = TrelloWebhookSetting(
                    webhook_id=ws.webhook_id,
                    event_type=ws.event_type,
                    enabled=True,
                    extra_config={
                        'label': ws.label,
                        'list_name': ws.list_name
                    }
                )
                db.session.add(tws)
                created_count += 1
        db.session.commit()
        return jsonify({'message': 'Fix applied', 'created': created_count}), 200
    except Exception as e:
        logger.error(f"Fix webhook settings failed: {e}")
        return jsonify({'error': 'Fix failed'}), 500

@app.route('/api/trello-webhook', methods=['GET', 'POST'])
def trello_webhook():
    logger.info("=== WEBHOOK ENDPOINT CALLED ===")
    try:
        if request.method == 'GET':
            logger.info("trello_webhook :: GET request received, returning challenge")
            return request.args.get('challenge', ''), 200

        payload = request.json
        logger.info(f"trello_webhook :: Received payload keys: {list(payload.keys())}")

        if not payload:
            logger.debug("trello_webhook :: No payload or action")
            return jsonify({'status': 'ignored', 'reason': 'No action in payload'}), 200

        action = payload.get('action')
        action_type = action.get('type') if action else None
        logger.info(f"trello_webhook :: Action type: {action_type}")

        board = action.get('data', {}).get('board', {}) if action else None
        board_id = board.get('id') if board else None
        board_name = board.get('name') if board else None

        # Map certain frontend event labels to Trello event types
        event_type_mapping = {
            'Mentioned in a card': 'commentCard',
            'Added to a card': 'addMemberToCard'
        }
        mapped_event_type = event_type_mapping.get(action_type, action_type)

        if not mapped_event_type:
            logger.debug("trello_webhook :: Mapped event type is None")
            return jsonify({'status': 'ignored', 'reason': 'Unsupported event type'}), 200

        # Find all users with webhook settings for this board and event type
        user_settings = WebhookSetting.query.filter_by(board_id=board_id, event_type=mapped_event_type).all()

        logger.info(f"trello_webhook :: Found {len(user_settings)} user settings for event {mapped_event_type}")
        
        if not user_settings:
            logger.debug(f"trello_webhook :: No user settings found for event type {mapped_event_type}")
            return jsonify({'status': 'ignored', 'reason': f'No user settings found for event type {mapped_event_type}'}), 200

        # Process event for each user who has settings for this event
        for user_setting in user_settings:
            logger.info(f"trello_webhook :: Processing for user {user_setting.user_email}")
            # Add user-specific context to the payload
            enriched_payload = {
                'trello_event': payload,
                'user_email': user_setting.user_email,
                'board_id': user_setting.board_id,
                'board_name': user_setting.board_name,
                'event_type': user_setting.event_type,
                'label': user_setting.label,
                'label_id': getattr(user_setting, 'label_id', None),
                'label_name': getattr(user_setting, 'label_name', None),
                'list_name': user_setting.list_name
            }
            logger.debug(f"trello_webhook :: Enqueuing task for user {user_setting.user_email}")
            q.enqueue(process_trello_event, enriched_payload)
        
        logger.info(f"trello_webhook :: Queued {len(user_settings)} tasks for event {mapped_event_type}")
        return jsonify({'status': 'queued', 'event_type': mapped_event_type, 'users_processed': len(user_settings)}), 200
    except Exception as e:
        logger.error(f"trello_webhook :: {e}");
        return jsonify({'status': 'failed', 'error': str(e)});

# Update Trello-related endpoints to check for Trello credentials
@app.route('/api/trello/verify', methods=['POST'])
@login_required
def trello_verify():

    user = current_user
    if not user.apiKey or not user.token:
        return jsonify({'error': 'Trello not linked'}), 400
    api_key = user.apiKey
    token = user.token
    url = f'https://api.trello.com/1/members/me?key={api_key}&token={token}'
    resp = requests.get(url)
    if resp.status_code != 200:
        return jsonify({'error': 'Invalid API Key or Token', 'details': resp.text}), 401
    return jsonify(resp.json()), 200

@app.route('/api/trello/boards', methods=['POST'])
@login_required
def trello_get_boards():
    user = current_user
    if not user.apiKey or not user.token:
        return jsonify({'error': 'Trello not linked'}), 400
    api_key = user.apiKey
    token = user.token
    boards_url = f'https://api.trello.com/1/members/me/boards?key={api_key}&token={token}'
    boards_resp = requests.get(boards_url)
    if boards_resp.status_code != 200:
        return jsonify({'error': 'Failed to fetch boards', 'details': boards_resp.text}), 400
    boards_data = boards_resp.json()
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

@app.route('/api/trello/labels', methods=['GET'])
@login_required
def trello_get_linked_board_labels():
    """Return labels for the user's linked/created board (UserBoard)."""
    user = current_user
    if not user.apiKey or not user.token:
        return jsonify({'error': 'Trello not linked'}), 400
    user_board = UserBoard.query.filter_by(user_email=user.email).first()
    if not user_board:
        return jsonify({'error': 'No linked board found'}), 404
    api_key = user.apiKey
    token = user.token
    labels_url = f'https://api.trello.com/1/boards/{user_board.board_id}/labels?key={api_key}&token={token}'
    resp = requests.get(labels_url)
    if resp.status_code != 200:
        return jsonify({'error': 'Failed to fetch labels', 'details': resp.text}), 400
    labels = resp.json()
    # Normalize shape
    normalized = [{
        'id': l.get('id'),
        'name': l.get('name') or '',
        'color': l.get('color')
    } for l in labels]
    return jsonify({'board_id': user_board.board_id, 'labels': normalized}), 200

@app.route('/api/trello/webhooks', methods=['POST'])
@login_required
def trello_register_webhook():
    data = request.json
    callback_url = data.get('callbackURL')
    board_id = data.get('idModel')
    description = data.get('description', '')
    event_settings = data.get('eventSettings', [])
    if not callback_url or not board_id:
        return jsonify({'error': 'Missing required fields'}), 400
    user = current_user
    if not user.apiKey or not user.token:
        return jsonify({'error': 'Trello not linked'}), 400
    api_key = user.apiKey
    token = user.token
    trello_webhook = TrelloWebhook.query.filter_by(board_id=board_id).first()
    if trello_webhook:
        webhook_id = trello_webhook.webhook_id
        for setting in event_settings:
            event_type = setting.get('event_type')
            enabled = setting.get('enabled', True)
            extra_config = setting.get('extra_config')
            upsert_trello_webhook_setting(webhook_id, event_type, enabled, extra_config)
        db.session.commit()
        return jsonify({'message': 'Webhook already exists, settings updated', 'id': webhook_id}), 200
    url = f'https://api.trello.com/1/webhooks'
    payload = {
        'key': api_key,
        'token': token,
        'callbackURL': callback_url,
        'idModel': board_id,
        'description': description
    }
    resp = requests.post(url, data=payload)
    if resp.status_code not in [200, 201]:
        try:
            err = resp.json()
            msg = err.get('message', 'Failed to register webhook')
        except Exception:
            msg = resp.text
        return jsonify({'error': msg}), 400
    webhook_data = resp.json()
    webhook_id = webhook_data.get('id')
    trello_webhook = TrelloWebhook(board_id=board_id, webhook_id=webhook_id, callback_url=callback_url)
    db.session.add(trello_webhook)
    db.session.commit()
    for setting in event_settings:
        event_type = setting.get('event_type')
        enabled = setting.get('enabled', True)
        extra_config = setting.get('extra_config')
        upsert_trello_webhook_setting(webhook_id, event_type, enabled, extra_config)
    db.session.commit()
    return jsonify({'message': 'Webhook registered and settings saved', 'id': webhook_id}), 201

@app.route('/api/trello/webhooks', methods=['GET'])
@login_required
def trello_get_webhooks():
    user = current_user
    if not user.apiKey or not user.token:
        return jsonify({'error': 'Trello not linked'}), 400
    api_key = user.apiKey
    token = user.token
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

@app.route('/api/trello/setup-board', methods=['POST'])
@login_required
def setup_trello_board():
    user = current_user
    if not user.apiKey or not user.token:
        return jsonify({'error': 'Trello not linked'}), 400
    api_key = user.apiKey
    token = user.token
    board_name = user.email.split('@')[0] if user.email and '@' in user.email else 'Integration Board'
    user_board = UserBoard.query.filter_by(user_email=user.email).first()
    if user_board:
        return jsonify({'message': 'Board already exists', 'board': user_board.to_dict()}), 200
    board_res = requests.post(
        f'https://api.trello.com/1/boards/',
        params={'name': board_name, 'defaultLists': 'false', 'key': api_key, 'token': token}
    )
    if board_res.status_code != 200:
        return jsonify({'error': 'Failed to create board', 'details': board_res.text}), 500
    board = board_res.json()
    board_id = board['id']
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
    user_board = UserBoard(user_email=user.email, board_id=board_id, board_name=board_name, lists=lists)
    db.session.add(user_board)
    db.session.commit()
    return jsonify({'message': 'Board created', 'board': user_board.to_dict()}), 201

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Docker health checks"""
    try:
        # Check database connection
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        # Check Redis connection if available
        if q and hasattr(q, 'connection') and q.connection:
            try:
                q.connection.ping()
            except Exception as redis_error:
                logger.warning(f"Redis health check failed: {redis_error}")
                # Don't fail health check for Redis issues
        return jsonify({'status': 'healthy', 'timestamp': time.time()}), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@app.route('/api/init-db', methods=['POST'])
def initialize_database():
    """Initialize database tables"""
    try:
        init_db()
        return jsonify({'message': 'Database initialized successfully'}), 200
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return jsonify({'error': f'Database initialization failed: {str(e)}'}), 500

@app.route('/admin/clear-db', methods=['POST'])
def clear_db():
    db.drop_all()
    db.create_all()
    return "Database cleared!", 200


if __name__ == '__main__':
    # Initialize database when app starts
    try:
        init_db()
    except Exception as e:
        logger.error(f"Failed to initialize database on startup: {e}")

    host = os.getenv('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_RUN_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1', 'yes']
    
    app.run(host=host, port=port, debug=debug)