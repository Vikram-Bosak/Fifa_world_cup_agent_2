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
    
    tweet = get_latest_photo_tweet(profiles, processed)
    if not tweet:
        logging.info("No new UNPROCESSED PHOTO tweet found across profiles.")
        send_telegram_message("Agent 1 Run: No new photo tweets found. Videos/GIFs were ignored.")
        return
        
    logging.info(f"Processing new photo tweet: {tweet['url']} from {tweet['profile']}")
    
    download_path = f"output/temp_agent1_{int(time.time())}.jpg"
    if download_image(tweet['image_url'], download_path):
        caption = (
            f"STATUS: DOWNLOADED\n"
            f"TITLE: {tweet['title'][:100]}...\n"
            f"SOURCE: {tweet['url']}\n"
            f"PROFILE: {tweet['profile']}\n"
            f"🕒 Time: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"
        )
        res = send_telegram_photo(download_path, caption)
        if res and res.get("ok"):
            msg_id = str(res['result']['message_id'])
            # Extract highest res photo file_id
            photos = res['result'].get('photo', [])
            file_id = photos[-1]['file_id'] if photos else None
            
            logging.info(f"Sent DOWNLOADED status to Telegram. Message ID: {msg_id}")
            
            # Save to JSON state manager
            update_post_status(
                post_id=tweet['url'],
                status="DOWNLOADED",
                telegram_msg_id=msg_id,
                telegram_file_id=file_id,
                title=tweet['title'],
                profile=tweet['profile']
            )
        else:
            logging.error("Failed to send photo to Telegram.")
            
        # Clean up image
        if os.path.exists(download_path):
            os.remove(download_path)
    else:
        logging.error("Failed to download image from Twitter.")

if __name__ == "__main__":
    load_dotenv()
    run_agent_1()
