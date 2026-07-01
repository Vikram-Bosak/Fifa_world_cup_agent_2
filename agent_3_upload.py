import os
import time
import random
import requests
import logging
from dotenv import load_dotenv
from src.telegram.reporter import download_telegram_photo, send_telegram_report_message
from src.state_manager import get_posts_by_status, update_post_status

# YouTube uploader import (graceful fallback if not available)
try:
    from src.youtube_uploader import upload_to_youtube
    YOUTUBE_AVAILABLE = True
except ImportError:
    try:
        from youtube_uploader import upload_to_youtube
        YOUTUBE_AVAILABLE = True
    except ImportError:
        YOUTUBE_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_page_access_token(user_token, page_id):
    """Resolve Page Access Token from User Access Token."""
    url = f"https://graph.facebook.com/v19.0/me/accounts?limit=100&access_token={user_token}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            for page in response.json().get('data', []):
                if str(page.get('id')) == str(page_id):
                    logging.info(f"Resolved Page Access Token for: {page.get('name')} ({page_id})")
                    return page.get('access_token')
            logging.warning(f"Page ID {page_id} not found. Using user token as fallback.")
        else:
            logging.warning(f"Failed to query /me/accounts (status {response.status_code}). Using user token.")
    except Exception as e:
        logging.error(f"Error resolving Page Access Token: {e}. Using user token.")
    return user_token

def upload_to_facebook(image_path, text_content):
    user_token = os.getenv("FACEBOOK_ACCESS_TOKEN")
    page_id = os.getenv("FACEBOOK_PAGE_ID", "me")
    
    if not user_token:
        logging.error("FACEBOOK_ACCESS_TOKEN is missing.")
        return False, None
    
    # Resolve Page Access Token
    access_token = get_page_access_token(user_token, page_id)
        
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
    logging.info("Starting Agent 3: Uploader (Facebook + YouTube Shorts)")
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
        
        fb_success = False
        yt_success = False
        
        try:
            if download_telegram_photo(file_id, upload_path):
                # Verify that the correct Content ID file exists
                if not os.path.exists(upload_path):
                    raise FileNotFoundError(f"Content ID mismatch: Expected {upload_path} not found.")
                
                # Apply human-like random delay before uploading
                # Delay between 1 minute (60s) and 5 minutes (300s)
                # Kept short to respect GitHub Actions 25-min timeout
                delay_seconds = random.randint(60, 300)
                delay_minutes = delay_seconds // 60
                logging.info(f"Applying random delay of {delay_minutes} minutes ({delay_seconds} seconds) for human-like behavior...")
                time.sleep(delay_seconds)
                
                facebook_text = data.get("facebook_post", f"{title}\n\n{description}")
                
                # ── Facebook Upload ──
                try:
                    success, fb_response = upload_to_facebook(upload_path, facebook_text)
                    if success and fb_response:
                        fb_post_id = fb_response
                        page_id = os.getenv("FACEBOOK_PAGE_ID", "me")
                        url_post_id = fb_post_id.split('_')[-1] if '_' in fb_post_id else fb_post_id
                        public_url = f"https://www.facebook.com/{page_id}/posts/{url_post_id}"
                        video_data = {"fb_url": public_url}
                        fb_success = True
                        logging.info(f"Successfully uploaded post {content_id} to Facebook.")
                    else:
                        video_data = {"fb_err": str(fb_response)}
                        logging.error(f"Failed to upload post {content_id} to Facebook: {fb_response}")
                except Exception as e:
                    video_data = {"fb_err": str(e)}
                    logging.error(f"Facebook upload exception for post {content_id}: {e}")

                # ── YouTube Shorts Upload (runs independently of Facebook) ──
                # YouTube Shorts requires a video file. FIFA 2 primarily processes images,
                # so this only runs if a video path is provided in the post data.
                video_path = data.get("video_path") or data.get("edited_video_path")
                if YOUTUBE_AVAILABLE and video_path and os.path.exists(video_path):
                    try:
                        logging.info("Waiting 2 seconds before uploading to YouTube Shorts...")
                        time.sleep(2)
                        yt_title = title[:100]  # YouTube title limit is 100 chars
                        yt_desc = f"{facebook_text}\n#shorts"
                        logging.info(f"Starting YouTube Shorts upload: title='{yt_title}'")
                        yt_url = upload_to_youtube(video_path, yt_title, yt_desc)  # type: ignore[reportPossiblyUnbound]
                        logging.info(f"Successfully uploaded to YouTube Shorts: {yt_url}")
                        video_data["yt_url"] = yt_url
                        yt_success = True
                    except Exception as e:
                        video_data["yt_err"] = str(e)
                        logging.error(f"Failed to upload to YouTube: {e}")
                elif not YOUTUBE_AVAILABLE:
                    logging.info("YouTube uploader not available — skipping YouTube upload.")
                else:
                    logging.info("No video file found for YouTube Shorts upload — skipping.")

                # ── Overall Status ──
                if fb_success or yt_success:
                    status_parts = []
                    if fb_success:
                        status_parts.append("Facebook")
                    if yt_success:
                        status_parts.append("YouTube")
                    logging.info(f"Upload completed successfully to: {', '.join(status_parts)}")

                    github_run_id = os.getenv('GITHUB_RUN_ID', 'manual')
                    report_lines = [
                        f"✅ Upload Successfully Completed",
                        f"🆔 Content ID: {content_id}\n",
                        f"🎬 Content Name:\n{title}\n",
                        f"📤 Upload Status: Success ({', '.join(status_parts)})\n",
                        f"🏷️ SEO Title:\n{title}\n",
                        f"📝 Description:\n{facebook_text}\n",
                        f"🔗 Source URL:\n{source_url}\n",
                        f"🕒 Upload Time:\n{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n",
                        f"📦 GitHub Repository:\nhttps://github.com/Vikram-Bosak/Fifa_world_cup_agent_2\n",
                        f"📄 Workflow Run:\nhttps://github.com/Vikram-Bosak/Fifa_world_cup_agent_2/actions/runs/{github_run_id}"
                    ]
                    if fb_success:
                        report_lines.append(f"\n📘 Facebook Post URL:\n{video_data.get('fb_url', 'N/A')}")
                    if yt_success:
                        report_lines.append(f"\n📺 YouTube Shorts URL:\n{video_data.get('yt_url', 'N/A')}")
                    
                    report_text = "\n".join(report_lines)
                    send_telegram_report_message(report_text, reply_to_message_id=msg_id)

                    # Build update kwargs based on what succeeded
                    update_kwargs = {"content_id": content_id, "status": "UPLOADED"}
                    if fb_success:
                        fb_post_id = video_data.get("fb_url", "").split("/")[-1] if video_data.get("fb_url") else "unknown"
                        update_kwargs["fb_post_id"] = fb_post_id
                        update_kwargs["public_url"] = video_data.get("fb_url", "")
                    if yt_success:
                        update_kwargs["yt_url"] = video_data.get("yt_url", "")
                    update_post_status(**update_kwargs)

                else:
                    error_msg = f"❌ <b>Error:</b> All uploads failed for post {content_id}"
                    if video_data.get("fb_err"):
                        error_msg += f"\nFacebook: {video_data['fb_err']}"
                    if video_data.get("yt_err"):
                        error_msg += f"\nYouTube: {video_data['yt_err']}"
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
            # Clean up — always runs regardless of outcome
            try:
                if os.path.exists(upload_path):
                    os.remove(upload_path)
                    logging.info(f"Cleaned up file: {upload_path}")
            except Exception as e:
                logging.warning(f"Failed to clean up file {upload_path}: {e}")

if __name__ == "__main__":
    load_dotenv()
    run_agent_3()
