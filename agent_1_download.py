import os
import time
import logging
from dotenv import load_dotenv
from src.scraper.twitter_scraper import get_latest_photo_tweet, download_image
from src.telegram.reporter import send_telegram_photo, send_telegram_message
from src.state_manager import load_state, update_post_status

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_agent_1():
    logging.info("Starting Agent 1: Downloader")
    # Supports multiple profiles separated by comma
    profiles_str = os.getenv("TWITTER_SOURCE_PROFILE", "FIFAWorldCup,Cristiano")
    profiles = [p.strip() for p in profiles_str.split(',') if p.strip()]
    
    state = load_state()
    processed = set(state.keys())
    
    try:
        tweet = get_latest_photo_tweet(profiles, processed)
    except Exception as e:
        error_msg = f"❌ <b>Error:</b> Failed to scan Twitter profiles: {e}"
        logging.error(error_msg)
        send_telegram_message(error_msg)
        return
        
    if not tweet:
        msg = "✅ <b>Pipeline Run Complete:</b> No new UNPROCESSED PHOTO tweet found."
        logging.info(msg)
        send_telegram_message(msg)
        return
        
    logging.info(f"Processing new photo tweet: {tweet['url']} from {tweet['profile']}")
    
    download_path = f"output/temp_agent1_{int(time.time())}.jpg"
    if download_image(tweet['image_url'], download_path):
        internal_post_id = f"FWC_{int(time.time())}"
        github_run_id = os.getenv('GITHUB_RUN_ID', 'manual')
        caption = (
            f"✅ Download Successfully Completed\n"
            f"🎬 Photo Name:\n{tweet['title'][:100]}\n\n"
            f"📥 Download Status: Success\n\n"
            f"👤 Source Profile:\n{tweet['profile']}\n\n"
            f"Original File: {internal_post_id}.jpg\n\n"
            f"🕒 Timestamp:\n{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n"
            f"📦 GitHub Repository:\nhttps://github.com/Vikram-Bosak/Fifa_world_cup_agent_2\n\n"
            f"📄 Workflow Run:\nhttps://github.com/Vikram-Bosak/Fifa_world_cup_agent_2/actions/runs/{github_run_id}"
        )
        res = send_telegram_photo(download_path, caption)
        if res and res.get("ok"):
            msg_id = str(res['result']['message_id'])
            # Extract highest res photo file_id
            photos = res['result'].get('photo', [])
            file_id = photos[-1]['file_id'] if photos else None
            
            logging.info(f"Sent DOWNLOADED status to Telegram. Message ID: {msg_id}")
            
            update_post_status(
                post_id=tweet['url'],
                status="DOWNLOADED",
                telegram_msg_id=msg_id,
                telegram_file_id=file_id,
                title=tweet['title'],
                profile=tweet['profile'],
                caption=tweet.get('caption', ''),
                internal_post_id=internal_post_id
            )
        else:
            error_msg = "❌ <b>Error:</b> Failed to send DOWNLOADED photo to Telegram."
            logging.error(error_msg)
            send_telegram_message(error_msg)
            
        # Clean up image
        if os.path.exists(download_path):
            os.remove(download_path)
    else:
        error_msg = f"❌ <b>Error:</b> Failed to download image from Twitter: {tweet['url']}"
        logging.error(error_msg)
        send_telegram_message(error_msg)

if __name__ == "__main__":
    load_dotenv()
    run_agent_1()
