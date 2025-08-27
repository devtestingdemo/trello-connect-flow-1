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
    def __init__(self, max_requests=100, per_seconds=10):
        self.max_requests = max_requests
        self.per_seconds = per_seconds
        self.request_times = deque()
        self.lock = Lock()

    def wait(self):
        with self.lock:
            now = time.time()
            while self.request_times and self.request_times[0] < now - self.per_seconds:
                self.request_times.popleft()
            if len(self.request_times) >= self.max_requests:
                sleep_time = self.per_seconds - (now - self.request_times[0])
                logger.info(f"[RateLimiter] Sleeping {sleep_time:.2f}s to avoid 429")
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
        label = enriched_payload.get('label')  # Keep for backward compatibility
        label_id = enriched_payload.get('label_id')
        label_name = enriched_payload.get('label_name')
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
            logger.debug(f"[Worker] Event type {trello_event_type} does not match setting {setting_event_type}")
            return
        trello_username = get_trello_username(user.apiKey, user.token)
        if not trello_username:
            logger.warning("Could not fetch Trello username, skipping.")
            return

        # Event-specific checks
        if trello_event_type == "commentCard":
            comment_text = trello_event['action']['data'].get('text', '')
            if f"@{trello_username}" not in comment_text:
                logger.debug("User not mentioned in comment, skipping.")
                return
        elif trello_event_type == "addMemberToCard":
            # Check if the user was added to the card
            member_added = trello_event['action']['member'].get('username') if trello_event['action'].get('member') else None
            if member_added != trello_username:
                logger.debug(f"User {trello_username} was not added to the card, skipping.")
                return

        api_key = user.apiKey
        token = user.token
        # Always copy to user's board and 'Enquiry In' list
        user_board = UserBoard.query.filter_by(user_email=user_email).first()
        if not user_board:
            logger.error(f"[Worker] No user board found for {user_email}")
            return
        target_board_id = user_board.board_id
        enquiry_in_list_id = user_board.lists.get('Enquiry In')
        if not enquiry_in_list_id:
            logger.error(f"[Worker] No 'Enquiry In' list found for user {user_email}")
            return
        # Copy the card to the user's board and 'Enquiry In' list
        copy_url = f"https://api.trello.com/1/cards?idCardSource={card_id}&idList={enquiry_in_list_id}&key={api_key}&token={token}"
        logger.debug("process_trello_event :: %s", copy_url)
        copy_resp = call_trello_api("POST", copy_url)
        if not copy_resp or copy_resp.status_code != 200:
            logger.error(f'[Worker] Failed to copy card {card_id}')
            return
        new_card = copy_resp.json()
        new_card_id = new_card.get('id')
        if not new_card_id:
            logger.error('[Worker] No new card id after copy')
            return

        # Link the main card to the copied card as an attachment
        main_card_url = f"https://trello.com/c/{card_id}"
        main_card_name = action.get('data', {}).get('card', {}).get('name', 'Main Card')
        attachment_url = f"https://api.trello.com/1/cards/{new_card_id}/attachments?key={api_key}&token={token}"
        attachment_payload = {
            "url": main_card_url,
            "name": f"Original Card: {main_card_name}"
        }
        attach_resp = call_trello_api("POST", attachment_url, json=attachment_payload)
        if not attach_resp or attach_resp.status_code not in [200, 201]:
            logger.warning(f"[Worker] Failed to attach main card link to copied card {new_card_id}")
        else:
            logger.info(f"[Worker] Linked main card {card_id} to copied card {new_card_id} as attachment.")

        # Apply label if specified
        if label_id:
            # Apply label by ID (preferred method)
            add_label_url = f"https://api.trello.com/1/cards/{new_card_id}/idLabels?key={api_key}&token={token}"
            label_resp = call_trello_api("POST", add_label_url, json={"value": label_id})
            if label_resp and label_resp.status_code in [200, 201]:
                logger.info(f'[Worker] Applied label {label_id} to card {new_card_id}')
            else:
                logger.warning(f'[Worker] Failed to apply label {label_id} to card {new_card_id}')
        elif label:
            # Fallback: Find label by name (for backward compatibility)
            labels_url = f"https://api.trello.com/1/boards/{target_board_id}/labels?key={api_key}&token={token}"
            labels_resp = call_trello_api("GET", labels_url)
            if labels_resp and labels_resp.status_code == 200:
                labels = labels_resp.json()
                label_obj = next((l for l in labels if l['name'] == label), None)
                if label_obj:
                    fallback_label_id = label_obj['id']
                    add_label_url = f"https://api.trello.com/1/cards/{new_card_id}/idLabels?key={api_key}&token={token}"
                    call_trello_api("POST", add_label_url, json={"value": fallback_label_id})
                    logger.info(f'[Worker] Applied label {label} (ID: {fallback_label_id}) to card {new_card_id}')
                else:
                    logger.warning(f'[Worker] Label {label} not found on board {target_board_id}')
            else:
                logger.error(f'[Worker] Failed to fetch labels for board {target_board_id}')
        
        logger.info(f'[Worker] Card {card_id} copied to {new_card_id} in list {enquiry_in_list_id} and label applied if specified.')

def call_trello_api(method, url, json=None):
    rate_limiter.wait()
    for attempt in range(3):
        resp = requests.request(method, url, json=json)
        if resp.status_code == 429:
            wait_time = 2 ** attempt
            logger.info(f"[Worker] 429 received. Backing off for {wait_time}s")
            time.sleep(wait_time)
        else:
            return resp
    logger.error("[Worker] Failed after retries")
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
