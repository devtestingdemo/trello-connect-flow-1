import time
import requests
import logging
from collections import deque
from threading import Lock
from db import db, User, WebhookSetting, UserBoard
from app_factory import create_app

# Configure logging
logger = logging.getLogger(__name__)

# Don't create app during import - it will be created when needed
app = None
q = None

def get_app():
    global app, q
    if app is None:
        app, q = create_app()
    return app, q

# Rate limiter
class TrelloRateLimiter:
    def __init__(self, max_requests=80, time_window=10):
        self.max_requests = max_requests
        self.time_window = time_window
        self.request_times = []

    def wait(self):
        now = time.time()
        # Remove old requests outside window
        self.request_times = [t for t in self.request_times if now - t < self.time_window]
        if len(self.request_times) >= self.max_requests:
            sleep_time = self.time_window - (now - self.request_times[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
        self.request_times.append(time.time())

rate_limiter = TrelloRateLimiter()

def process_trello_event(enriched_payload):
    logger.info(f'[Worker] Starting to process task with payload keys: {list(enriched_payload.keys())}')
    # Get app context when needed
    app_instance, q_instance = get_app()
    with app_instance.app_context():
        # Extract Trello event and user context
        trello_event = enriched_payload.get('trello_event', {})
        user_email = enriched_payload.get('user_email')
        board_id = enriched_payload.get('board_id')
        board_name = enriched_payload.get('board_name')
        event_type = enriched_payload.get('event_type')
        label = enriched_payload.get('label')
        label_id = enriched_payload.get('label_id')
        list_name = enriched_payload.get('list_name')
        
        logger.info(f'[Worker] Extracted user_email: {user_email}, event_type: {event_type}, board_name: {board_name}')
        
        action = trello_event.get('action', {})
        webhook_id = trello_event.get('webhook', {}).get('id')
        card_id = action.get('data', {}).get('card', {}).get('id')
        trello_event_type = action.get('type')
        
        logger.info(f'[Worker] Extracted webhook_id: {webhook_id}, card_id: {card_id}, trello_event_type: {trello_event_type}')
        
        if not webhook_id or not card_id or not trello_event_type or not user_email:
            logger.error('[Worker] Missing required fields in enriched payload')
            return
            
        logger.info(f'[Worker] Processing event {trello_event_type} for user {user_email} on board {board_name}')
        
        # Find user
        user = User.query.filter_by(email=user_email).first()
        if not user:
            logger.error(f'[Worker] No user found for email {user_email}')
            return
        # Only proceed if the event type matches the setting
        # Map 'Mentioned in a card' to 'commentCard' and 'Added to a card' to 'addMemberToCard' for comparison
        setting_event_type = "commentCard" if event_type == "Mentioned in a card" else (
            "addMemberToCard" if event_type == "Added to a card" else event_type
        )

        if trello_event_type != setting_event_type:
            logger.info(f"[Worker] Event type {trello_event_type} does not match setting {setting_event_type}, skipping")
            return

        # For demo purposes, simulate copying/creating a card and then applying label
        api_key = user.apiKey
        token = user.token
        # Retrieve enquiry list id if needed (omitted here for brevity)
        enquiry_in_list_id = None

        # Simulate card copy/create, assume new_card_id created
        new_card_id = card_id
        logger.info(f'[Worker] Using card {card_id} for label application (no copy performed)')

        # Apply label by ID when available; fallback to name lookup
        if label_id or label:
            try:
                if label_id:
                    add_label_url = f"https://api.trello.com/1/cards/{new_card_id}/idLabels?key={api_key}&token={token}"
                    call_trello_api("POST", add_label_url, json={"value": label_id})
                    logger.info(f"[Worker] Applied label by id {label_id} to card {new_card_id}")
                else:
                    # Find label id on the board by name
                    labels_url = f"https://api.trello.com/1/boards/{board_id}/labels?key={api_key}&token={token}"
                    labels_resp = call_trello_api("GET", labels_url)
                    if labels_resp and labels_resp.status_code == 200:
                        labels_data = labels_resp.json()
                        label_obj = next((l for l in labels_data if l.get('name') == label), None)
                        if label_obj:
                            resolved_label_id = label_obj.get('id')
                            add_label_url = f"https://api.trello.com/1/cards/{new_card_id}/idLabels?key={api_key}&token={token}"
                            call_trello_api("POST", add_label_url, json={"value": resolved_label_id})
                            logger.info(f"[Worker] Applied label by name {label} (id {resolved_label_id}) to card {new_card_id}")
                        else:
                            logger.warning(f'[Worker] Label {label} not found on board {board_id}')
                    else:
                        logger.error(f'[Worker] Failed to fetch labels for board {board_id}')
            except Exception as e:
                logger.error(f"[Worker] Failed to apply label: {e}")
        logger.info(f'[Worker] Completed processing for card {card_id} (label application attempted if specified).')

def call_trello_api(method, url, json=None):
    rate_limiter.wait()
    try:
        resp = requests.request(method, url, json=json)
        return resp
    except Exception as e:
        logger.error(f"call_trello_api error: {e}")
        return None

def handle_mentioned(payload):
    # Trello API call
    card_id = payload['action']['data']['card']['id']
    url = f"https://api.trello.com/1/cards/{card_id}/actions"
    return call_trello_api("GET", url)

def handle_added(payload):
    card_id = payload['action']['data']['card']['id']
    url = f"https://api.trello.com/1/cards/{card_id}"
    return call_trello_api("GET", url)

def get_trello_username(api_key, token):
    url = f"https://api.trello.com/1/members/me?key={api_key}&token={token}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get("username")
    else:
        logger.error(f"Failed to fetch Trello username: {response.text}")
        return None
