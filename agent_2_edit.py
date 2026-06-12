import os
import time
import logging
from dotenv import load_dotenv
from src.telegram.reporter import download_telegram_photo, send_telegram_photo
from src.image_editor.processor import add_watermark
from src.state_manager import get_posts_by_status, update_post_status

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_agent_2():
    logging.info("Starting Agent 2: Editor")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not bot_token:
        logging.error("Telegram bot token missing.")
        return
        
    pending_posts = get_posts_by_status("DOWNLOADED")
    if not pending_posts:
        logging.info("No DOWNLOADED posts to edit.")
        return
        
    for post_id, data in pending_posts.items():
        file_id = data.get("telegram_file_id")
        title = data.get("title", "FIFA Update")
        msg_id = data.get("telegram_msg_id")
        
        if not file_id:
            logging.error(f"Missing file_id for post {post_id}")
            continue
            
        logging.info(f"Processing DOWNLOADED message: {msg_id}")
        
        raw_path = f"output/raw_{msg_id}.jpg"
        edited_path = f"output/edited_{msg_id}.jpg"
        
        if download_telegram_photo(file_id, raw_path):
            # Edit Image
            if add_watermark(raw_path, edited_path, logo_path="assets/logo/logo.png"):
                # Generate Unique Post ID
                internal_post_id = f"FWC_{int(time.time())}"
                
                report = (
                    f"STATUS: EDITED\n"
                    f"POST_ID: {internal_post_id}\n"
                    f"TITLE: {title}\n"
                    f"🕒 Time: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"
                )
                
                res = send_telegram_photo(edited_path, report)
                if res and res.get("ok"):
                    new_msg_id = str(res['result']['message_id'])
                    photos = res['result'].get('photo', [])
                    new_file_id = photos[-1]['file_id'] if photos else None
                    
                    logging.info(f"Sent EDITED status. New Message ID: {new_msg_id}")
                    
                    update_post_status(
                        post_id=post_id,
                        status="EDITED",
                        telegram_msg_id=new_msg_id,
                        telegram_file_id=new_file_id,
                        internal_post_id=internal_post_id
                    )
                else:
                    logging.error(f"Failed to send EDITED photo for {post_id}")
            
            # Clean up files
            for p in [raw_path, edited_path]:
                if os.path.exists(p):
                    os.remove(p)

if __name__ == "__main__":
    load_dotenv()
    run_agent_2()

