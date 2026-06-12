import os
import json
import logging

STATE_FILE = "output/pipeline_state.json"

def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load state from {STATE_FILE}: {e}")
        return {}

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        logging.error(f"Failed to save state to {STATE_FILE}: {e}")

def update_post_status(post_id, status, **kwargs):
    """
    Updates the status of a specific post_id.
    post_id is generally the tweet url or internal ID.
    kwargs can be any additional metadata (telegram_msg_id, title, etc.)
    """
    state = load_state()
    if post_id not in state:
        state[post_id] = {}
        
    state[post_id]["status"] = status
    for k, v in kwargs.items():
        state[post_id][k] = v
        
    save_state(state)
    return state[post_id]

def get_posts_by_status(status):
    state = load_state()
    return {k: v for k, v in state.items() if v.get("status") == status}
