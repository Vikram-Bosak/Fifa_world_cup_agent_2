import os
import time
import requests
import logging
from dotenv import load_dotenv
from src.telegram.reporter import download_telegram_photo, send_telegram_message

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_processed_msgs():
    if not os.path.exists("output/processed_agent3.txt"):
        return set()
    with open("output/processed_agent3.txt", "r") as f:
        return set(line.strip() for line in f)

def save_processed_msg(msg_id):
    os.makedirs("output", exist_ok=True)
    with open("output/processed_agent3.txt", "a") as f:
        f.write(f"{msg_id}\n")

def upload_to_facebook(image_path, text_content):
    access_token = os.getenv("FACEBOOK_ACCESS_TOKEN")
    page_id = os.getenv("FACEBOOK_PAGE_ID", "me")
    
    if not access_token:
        logging.error("FACEBOOK_ACCESS_TOKEN is missing.")
        return False, None
        
    url = f"https://graph.facebook.com/{page_id}/photos"
    try:
        with open(image_path, 'rb') as image_file:
            files = {'source': image_file}
            data = {'message': text_content, 'access_token': access_token}
            response = requests.post(url, files=files, data=data)
            response.raise_for_status()
            result = response.json()
            post_id = result.get('post_id', result.get('id'))
            return True, post_id
    except Exception as e:
        logging.error(f"Failed to upload to Facebook: {e}")
        return False, None

def run_agent_3():
    logging.info("Starting Agent 3: Uploader")
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
        
        if "STATUS: EDITED" in caption and msg_id not in processed:
            logging.info(f"Found EDITED message: {msg_id}")
            
            photos = message.get('photo')
            if not photos:
                continue
                
            file_id = photos[-1]['file_id']
            upload_path = f"output/upload_{msg_id}.jpg"
            
            if download_telegram_photo(file_id, upload_path):
                # Extract Title and Post ID
                title = "FIFA Update"
                post_id_internal = "UNKNOWN"
                for line in caption.split('\n'):
                    if line.startswith("TITLE:"):
                        title = line.replace("TITLE:", "").strip()
                    elif line.startswith("POST_ID:"):
                        post_id_internal = line.replace("POST_ID:", "").strip()
                
                facebook_text = f"⚽ FIFA World Cup Update 🏆\n\n{title}\n\n#FIFAWorldCup #Football #Soccer"
                
                success, fb_post_id = upload_to_facebook(upload_path, facebook_text)
                if success and fb_post_id:
                    page_id = os.getenv("FACEBOOK_PAGE_ID", "me")
                    url_post_id = fb_post_id.split('_')[-1] if '_' in fb_post_id else fb_post_id
                    public_url = f"https://www.facebook.com/{page_id}/posts/{url_post_id}"
                    
                    report_text = (
                        f"✅ <b>STATUS: SUCCESS</b>\n\n"
                        f"📝 <b>Title:</b> {title}\n"
                        f"🆔 <b>Internal Post ID:</b> {post_id_internal}\n"
                        f"🌐 <b>Facebook Post ID:</b> {fb_post_id}\n"
                        f"⏱️ <b>Time:</b> {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n"
                        f"🔗 <a href='{public_url}'>View on Facebook</a>"
                    )
                    send_telegram_message(report_text, reply_to_message_id=msg_id)
                    save_processed_msg(msg_id)
                    logging.info("Successfully processed 1 post. Stopping.")
                    break

if __name__ == "__main__":
    load_dotenv()
    run_agent_3()
