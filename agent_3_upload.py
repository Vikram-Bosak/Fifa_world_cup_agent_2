import os
import time
import random
import requests
import logging
from dotenv import load_dotenv
from src.telegram.reporter import download_telegram_photo, send_telegram_report_message
from src.state_manager import get_posts_by_status, update_post_status

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def upload_to_facebook(image_path, text_content):
    access_token = os.getenv("FACEBOOK_ACCESS_TOKEN")
    page_id = os.getenv("FACEBOOK_PAGE_ID", "me")
    
    if not access_token:
        logging.error("FACEBOOK_ACCESS_TOKEN is missing.")
        return False, None
        
    url = f"https://graph.facebook.com/v19.0/{page_id}/photos"
    from src.http_client import get_retry_session
    try:
        session = get_retry_session(retries=3)
        with open(image_path, 'rb') as image_file:
            files = {'source': ('image.jpg', image_file, 'image/jpeg')}
            data = {'message': text_content}
            params = {'access_token': access_token}
            response = session.post(url, files=files, data=data, params=params, timeout=30)
            response.raise_for_status()
            result = response.json()
            post_id = result.get('post_id', result.get('id'))
            return True, post_id
    except requests.exceptions.HTTPError as e:
        error_details = e.response.text if e.response else str(e)
        logging.error(f"Failed to upload to Facebook (HTTP Error): {error_details}")
        return False, f"API Error: {error_details}"
    except Exception as e:
        logging.error(f"Failed to upload to Facebook: {e}")
        return False, str(e)

def run_agent_3():
    logging.info("Starting Agent 3: Uploader")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not bot_token:
        logging.error("Telegram bot token missing.")
        return
        
    pending_posts = get_posts_by_status("EDITED")
    if not pending_posts:
        logging.info("No EDITED posts to upload.")
        return
        
    for content_id, data in pending_posts.items():
        file_id = data.get("telegram_file_id")
        title = data.get("title", "FIFA Update")
        description = data.get("caption", "")
        msg_id = data.get("telegram_msg_id")
        source_url = data.get("source_url", "UNKNOWN")
        
        if not file_id:
            logging.error(f"Missing file_id for post {content_id}")
            continue
            
        logging.info(f"Processing EDITED message: {msg_id} (Content ID: {content_id})")
        
        upload_path = f"output/{content_id}_final.jpg"
        
        try:
            if download_telegram_photo(file_id, upload_path):
                # Verify that the correct Content ID file exists
                if not os.path.exists(upload_path):
                    raise FileNotFoundError(f"Content ID mismatch: Expected {upload_path} not found.")
                
                # Apply human-like random delay before uploading
                # Delay between 2 minutes (120s) and 15 minutes (900s)
                delay_seconds = random.randint(120, 900)
                delay_minutes = delay_seconds // 60
                logging.info(f"Applying random delay of {delay_minutes} minutes ({delay_seconds} seconds) for human-like behavior...")
                time.sleep(delay_seconds)
                
                facebook_text = data.get("facebook_post", f"{title}\n\n{description}")
                
                success, fb_response = upload_to_facebook(upload_path, facebook_text)
                if success and fb_response:
                    fb_post_id = fb_response
                    page_id = os.getenv("FACEBOOK_PAGE_ID", "me")
                    url_post_id = fb_post_id.split('_')[-1] if '_' in fb_post_id else fb_post_id
                    public_url = f"https://www.facebook.com/{page_id}/posts/{url_post_id}"
                    
                    github_run_id = os.getenv('GITHUB_RUN_ID', 'manual')
                    report_text = (
                        f"✅ Upload Successfully Completed\n"
                        f"🆔 Content ID: {content_id}\n\n"
                        f"🎬 Photo Name:\n{title}\n\n"
                        f"📤 Facebook Upload Status: Success\n\n"
                        f"🏷️ SEO Title:\n{title}\n\n"
                        f"📝 Description:\n{facebook_text}\n\n"
                        f"🔗 Source URL:\n{source_url}\n\n"
                        f"Facebook Post ID: {fb_post_id}\n\n"
                        f"🔗 Facebook Photo Post URL:\n{public_url}\n\n"
                        f"🕒 Upload Time:\n{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n"
                        f"📦 GitHub Repository:\nhttps://github.com/Vikram-Bosak/Fifa_world_cup_agent_2\n\n"
                        f"📄 Workflow Run:\nhttps://github.com/Vikram-Bosak/Fifa_world_cup_agent_2/actions/runs/{github_run_id}"
                    )
                    send_telegram_report_message(report_text, reply_to_message_id=msg_id)
                    
                    update_post_status(
                        content_id=content_id,
                        status="UPLOADED",
                        fb_post_id=fb_post_id,
                        public_url=public_url
                    )
                    logging.info(f"Successfully uploaded post {content_id} to Facebook.")
                else:
                    error_msg = f"❌ <b>Error:</b> Failed to upload post {content_id} to Facebook.\nDetails: {fb_response}"
                    logging.error(error_msg)
                    send_telegram_report_message(error_msg, reply_to_message_id=msg_id)
            else:
                error_msg = f"❌ <b>Error:</b> Failed to download edited photo from Telegram for upload (Post {content_id})"
                logging.error(error_msg)
                send_telegram_report_message(error_msg, reply_to_message_id=msg_id)
        except Exception as e:
            error_msg = f"❌ <b>Error:</b> Exception during upload process: {e}"
            logging.error(error_msg)
            send_telegram_report_message(error_msg, reply_to_message_id=msg_id)
        finally:
            # Clean up
            if os.path.exists(upload_path):
                os.remove(upload_path)

if __name__ == "__main__":
    load_dotenv()
    run_agent_3()

