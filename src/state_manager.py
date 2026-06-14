import os
import json
import logging

import datetime

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

def generate_content_id():
    state = load_state()
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    prefix = f"FIFA-{today_str}-"
    
    # Find max sequence for today
    max_seq = 0
    for cid in state.keys():
        if cid.startswith(prefix):
            try:
                seq = int(cid.split("-")[-1])
                if seq > max_seq:
                    max_seq = seq
            except ValueError:
                pass
                
    new_seq = max_seq + 1
    return f"{prefix}{new_seq:04d}"

def update_post_status(content_id, status, **kwargs):
    """
    Updates the status of a specific content_id.
    """
    state = load_state()
    if content_id not in state:
        state[content_id] = {}
        
    state[content_id]["status"] = status
    
    # Add timestamp based on status
    current_time = datetime.datetime.utcnow().isoformat() + "Z"
    if status == "DOWNLOADED" and "download_time" not in state[content_id]:
        state[content_id]["download_time"] = current_time
    elif status == "EDITED" and "edit_time" not in state[content_id]:
        state[content_id]["edit_time"] = current_time
    elif status == "UPLOADED" and "upload_time" not in state[content_id]:
        state[content_id]["upload_time"] = current_time
        
    for k, v in kwargs.items():
        state[content_id][k] = v
        
    save_state(state)
    return state[content_id]

def get_posts_by_status(status):
    state = load_state()
    return {k: v for k, v in state.items() if v.get("status") == status}
