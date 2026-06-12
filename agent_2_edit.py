import os
import time
import logging
from dotenv import load_dotenv
from src.telegram.reporter import download_telegram_photo, send_telegram_photo, send_telegram_message
from src.image_editor.processor import add_watermark
from src.state_manager import get_posts_by_status, update_post_status
from src.ai_generator import generate_headline

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
        description = data.get("caption", "")
        msg_id = data.get("telegram_msg_id")
        
        if not file_id:
            logging.error(f"Missing file_id for post {post_id}")
            continue
            
        logging.info(f"Processing DOWNLOADED message: {msg_id}")
        
        raw_path = f"output/raw_{msg_id}.jpg"
        edited_path = f"output/edited_{msg_id}.jpg"
        
        internal_post_id = data.get("internal_post_id", "UNKNOWN")
        
        try:
            if download_telegram_photo(file_id, raw_path):
                # Generate AI Headline
                headline = generate_headline(title, description)
                
                # Edit Image
                if add_watermark(raw_path, edited_path, logo_path="assets/logo/logo.png", watermark_text=headline):
                    github_run_id = os.getenv('GITHUB_RUN_ID', 'manual')
                    report = (
                        f"✅ Editing Successfully Completed\n"
                        f"🎬 Photo Name:\n{title}\n\n"
                        f"🛠️ Editing Status: Success\n\n"
                        f"📝 Applied Edits:\nAI Headline added, Branding Watermark\n\n"
                        f"Original File: {internal_post_id}.jpg\n\n"
                        f"🕒 Timestamp:\n{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n"
                        f"📦 GitHub Repository:\nhttps://github.com/Vikram-Bosak/Fifa_world_cup_agent_2\n\n"
                        f"📄 Workflow Run:\nhttps://github.com/Vikram-Bosak/Fifa_world_cup_agent_2/actions/runs/{github_run_id}"
                    )
                    
                    res = send_telegram_photo(edited_path, report, reply_to_message_id=msg_id)
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
                        error_msg = f"❌ <b>Error:</b> Failed to send EDITED photo for {post_id}"
                        logging.error(error_msg)
                        send_telegram_message(error_msg, reply_to_message_id=msg_id)
                else:
                    error_msg = f"❌ <b>Error:</b> Failed to add watermark/edit image for {post_id}"
                    logging.error(error_msg)
                    send_telegram_message(error_msg, reply_to_message_id=msg_id)
            else:
                error_msg = f"❌ <b>Error:</b> Failed to download photo from Telegram for editing (Post {post_id})"
                logging.error(error_msg)
                send_telegram_message(error_msg, reply_to_message_id=msg_id)
        except Exception as e:
            error_msg = f"❌ <b>Error:</b> Exception during editing process: {e}"
            logging.error(error_msg)
            send_telegram_message(error_msg, reply_to_message_id=msg_id)
        finally:
            # Clean up files
            for p in [raw_path, edited_path]:
                if os.path.exists(p):
                    os.remove(p)

if __name__ == "__main__":
    load_dotenv()
    run_agent_2()

