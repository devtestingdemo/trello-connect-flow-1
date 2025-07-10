import time
import requests
from collections import deque
from threading import Lock
from db import db, User, WebhookSetting, UserBoard
from app_factory import create_app
app, q = create_app()
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
                print(f"[RateLimiter] Sleeping {sleep_time:.2f}s to avoid 429")
                time.sleep(sleep_time)
            self.request_times.append(time.time())

rate_limiter = TrelloRateLimiter()

def process_trello_event(payload):
    with app.app_context():
        action = payload.get('action', {})
        webhook_id = payload.get('webhook', {}).get('id')
        card_id = action.get('data', {}).get('card', {}).get('id')
        event_type = action.get('type')
        if not webhook_id or not card_id or not event_type:
            print('[Worker] Missing webhook_id, card_id, or event_type in payload')
            return
        # Find webhook setting
        setting = WebhookSetting.query.filter_by(webhook_id=webhook_id).first()
        if not setting:
            print(f'[Worker] No webhook setting found for webhook_id {webhook_id}')
            return
        # Only proceed if the event type matches the setting
        # Map 'Mentioned in a card' to 'commentCard' for comparison
        setting_event_type = "commentCard" if setting.event_type == "Mentioned in a card" else setting.event_type

        if event_type != setting_event_type:
            print(f"[Worker] Event type {event_type} does not match setting {setting_event_type}")
            return
        user = User.query.filter_by(email=setting.user_email).first()
        if not user:
            print(f'[Worker] No user found for email {setting.user_email}')
            return
        trello_username = get_trello_username(user.apiKey, user.token)
        if not trello_username:
            print("Could not fetch Trello username, skipping.")
            return

        comment_text = payload['action']['data'].get('text', '')
        if f"@{trello_username}" not in comment_text:
            print("User not mentioned in comment, skipping.")
            return

        api_key = user.apiKey
        token = user.token
        # Always copy to user's board and 'Enquiry In' list
        user_board = UserBoard.query.filter_by(user_email=setting.user_email).first()
        if not user_board:
            print(f"[Worker] No user board found for {setting.user_email}")
            return
        board_id = user_board.board_id
        enquiry_in_list_id = user_board.lists.get('Enquiry In')
        if not enquiry_in_list_id:
            print(f"[Worker] No 'Enquiry In' list found for user {setting.user_email}")
            return
        # Copy the card to the user's board and 'Enquiry In' list
        copy_url = f"https://api.trello.com/1/cards?idCardSource={card_id}&idList={enquiry_in_list_id}&key={api_key}&token={token}"
        print("process_trello_event :: ", copy_url)
        copy_resp = call_trello_api("POST", copy_url)
        if not copy_resp or copy_resp.status_code != 200:
            print(f'[Worker] Failed to copy card {card_id}')
            return
        new_card = copy_resp.json()
        new_card_id = new_card.get('id')
        if not new_card_id:
            print('[Worker] No new card id after copy')
            return
        # Apply label if specified
        if setting.label:
            # Find label id on the board
            labels_url = f"https://api.trello.com/1/boards/{board_id}/labels?key={api_key}&token={token}"
            labels_resp = call_trello_api("GET", labels_url)
            if labels_resp and labels_resp.status_code == 200:
                labels = labels_resp.json()
                label_obj = next((l for l in labels if l['name'] == setting.label), None)
                if label_obj:
                    label_id = label_obj['id']
                    add_label_url = f"https://api.trello.com/1/cards/{new_card_id}/idLabels?key={api_key}&token={token}"
                    call_trello_api("POST", add_label_url, json={"value": label_id})
                else:
                    print(f'[Worker] Label {setting.label} not found on board {board_id}')
            else:
                print(f'[Worker] Failed to fetch labels for board {board_id}')
        print(f'[Worker] Card {card_id} copied to {new_card_id} in list {enquiry_in_list_id} and label applied if specified.')

def call_trello_api(method, url, json=None):
    rate_limiter.wait()
    for attempt in range(3):
        resp = requests.request(method, url, json=json)
        if resp.status_code == 429:
            wait_time = 2 ** attempt
            print(f"[Worker] 429 received. Backing off for {wait_time}s")
            time.sleep(wait_time)
        else:
            return resp
    print("[Worker] Failed after retries")

def handle_mentioned(payload):
    # Trello API call
    card_id = payload['action']['data']['card']['id']
    url = f"https://api.trello.com/1/cards/{card_id}/actions"
    call_trello_api("GET", url)

def handle_added(payload):
    card_id = payload['action']['data']['card']['id']
    url = f"https://api.trello.com/1/cards/{card_id}"
    call_trello_api("GET", url)

def get_trello_username(api_key, token):
    url = f"https://api.trello.com/1/members/me?key={api_key}&token={token}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get("username")
    else:
        print(f"Failed to fetch Trello username: {response.text}")
        return None
