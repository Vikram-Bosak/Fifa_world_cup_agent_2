import os
import time
import logging
from dotenv import load_dotenv
from src.telegram.reporter import download_telegram_photo, send_telegram_photo, send_telegram_message
from src.image_editor.processor import create_football_post
from src.state_manager import get_posts_by_status, update_post_status
from src.ai_generator import analyze_and_generate_content

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_agent_2():
    from src.limits import can_edit, increment_edit
    
    logging.info("Starting Agent 2: Editor")
    
    if not can_edit():
        logging.info("Daily edit limit reached (5/day). Skipping.")
        return
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not bot_token:
        logging.error("Telegram bot token missing.")
        return
        
    pending_posts = get_posts_by_status("DOWNLOADED")
    if not pending_posts:
        logging.info("No DOWNLOADED posts to edit.")
        return
        
    for content_id, data in pending_posts.items():
        file_id = data.get("telegram_file_id")
        title = data.get("title", "FIFA Update")
        description = data.get("caption", "")
        msg_id = data.get("telegram_msg_id")
        
        if not file_id:
            logging.error(f"Missing file_id for post {content_id}")
            continue
            
        logging.info(f"Processing DOWNLOADED message: {msg_id} (Content ID: {content_id})")
        
        raw_path = f"output/{content_id}_raw.jpg"
        edited_path = f"output/{content_id}_edited.jpg"
        
        try:
            if download_telegram_photo(file_id, raw_path):
                # Verify that the correct Content ID file exists
                if not os.path.exists(raw_path):
                    raise FileNotFoundError(f"Content ID mismatch: Expected {raw_path} not found.")
                
                # Content Analysis and Generation
                ai_data = analyze_and_generate_content(title, description)
                headline = ai_data.get("image_headline", title[:50])
                subheadline = ai_data.get("image_subheadline", description[:100])
                facebook_post = ai_data.get("facebook_post", f"{title}\n\n{description}")
                style = ai_data.get("style", "News Style")
                confidence = ai_data.get("confidence", "50")
                
                logging.info(f"Generated Style: {style} (Confidence: {confidence}%)")
                
                # Edit Image
                if create_football_post(raw_path, edited_path, headline=headline, hook_text=subheadline, branding="FIFA Insider USA", style=style, logo_path="assets/logo/logo.png"):
                    github_run_id = os.getenv('GITHUB_RUN_ID', 'manual')
                    report = (
                        f"✅ Editing Successfully Completed\n"
                        f"🆔 Content ID: {content_id}\n\n"
                        f"🎬 Original Title:\n{title}\n\n"
                        f"🛠️ Editing Status: Success\n\n"
                        f"Detected Editing Style: {style} (Confidence: {confidence}%)\n\n"
                        f"📝 Generated Headline:\n{headline}\n\n"
                        f"📝 Generated Subheadline:\n{subheadline}\n\n"
                        f"Original File: {content_id}_raw.jpg\n"
                        f"Edited File: {content_id}_edited.jpg\n\n"
                        f"🕒 Edit Time:\n{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n"
                        f"📦 GitHub Repository:\nhttps://github.com/Vikram-Bosak/Fifa_world_cup_agent_2\n\n"
                        f"📄 Workflow Run:\nhttps://github.com/Vikram-Bosak/Fifa_world_cup_agent_2/actions/runs/{github_run_id}"
                    )
                    
                    res = send_telegram_photo(edited_path, report, reply_to_message_id=msg_id)
                    if res and res.get("ok"):
                        new_msg_id = str(res['result']['message_id'])
                        photos = res['result'].get('photo', [])
                        new_file_id = photos[-1]['file_id'] if photos else None
                        
                        logging.info(f"Sent EDITED status. New Message ID: {new_msg_id}")
                    increment_edit()
                        
                        update_post_status(
                            content_id=content_id,
                            status="EDITED",
                            telegram_msg_id=new_msg_id,
                            telegram_file_id=new_file_id,
                            facebook_post=facebook_post
                        )
                    else:
                        error_msg = f"❌ <b>Error:</b> Failed to send EDITED photo for {content_id}"
                        logging.error(error_msg)
                        send_telegram_message(error_msg, reply_to_message_id=msg_id)
                else:
                    error_msg = f"❌ <b>Error:</b> Failed to add watermark/edit image for {content_id}"
                    logging.error(error_msg)
                    send_telegram_message(error_msg, reply_to_message_id=msg_id)
            else:
                error_msg = f"❌ <b>Error:</b> Failed to download photo from Telegram for editing (Post {content_id})"
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

