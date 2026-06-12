import os
import time
import requests
import logging
from dotenv import load_dotenv
from src.telegram.reporter import download_telegram_photo, send_telegram_photo
from src.image_editor.processor import add_watermark

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_processed_msgs():
    if not os.path.exists("output/processed_agent2.txt"):
        return set()
    with open("output/processed_agent2.txt", "r") as f:
        return set(line.strip() for line in f)

def save_processed_msg(msg_id):
    os.makedirs("output", exist_ok=True)
    with open("output/processed_agent2.txt", "a") as f:
        f.write(f"{msg_id}\n")

def run_agent_2():
    logging.info("Starting Agent 2: Editor")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not bot_token:
        logging.error("Telegram bot token missing.")
        return
        
    processed = load_processed_msgs()
    
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    try:
        response = requests.get(url)
        updates = response.json().get('result', [])
    except Exception as e:
        logging.error(f"Error fetching updates: {e}")
        return
        
    for update in sorted(updates, key=lambda x: x.get('update_id', 0)):
        message = update.get('channel_post') or update.get('message')
        if not message:
            continue
            
        msg_id = str(message.get('message_id'))
        caption = message.get('caption', '')
        
        if "STATUS: DOWNLOADED" in caption and msg_id not in processed:
            logging.info(f"Found DOWNLOADED message: {msg_id}")
            
            photos = message.get('photo')
            if not photos:
                continue
                
            file_id = photos[-1]['file_id']
            raw_path = f"output/raw_{msg_id}.jpg"
            edited_path = f"output/edited_{msg_id}.jpg"
            
            if download_telegram_photo(file_id, raw_path):
                # Edit Image
                if add_watermark(raw_path, edited_path, logo_path="assets/logo/logo.png"):
                    # Generate Unique Post ID
                    post_id = f"FWC_{int(time.time())}"
                    
                    # Extract TITLE
                    title = "FIFA Update"
                    for line in caption.split('\n'):
                        if line.startswith("TITLE:"):
                            title = line.replace("TITLE:", "").strip()
                            break
                            
                    report = (
                        f"STATUS: EDITED\n"
                        f"POST_ID: {post_id}\n"
                        f"TITLE: {title}\n"
                        f"🕒 Time: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"
                    )
                    
                    res = send_telegram_photo(edited_path, report)
                    if res and res.get("ok"):
                        logging.info(f"Sent EDITED status. New Message ID: {res['result']['message_id']}")
                        save_processed_msg(msg_id)
                        break # Process 1 at a time
                        
if __name__ == "__main__":
    load_dotenv()
    run_agent_2()
