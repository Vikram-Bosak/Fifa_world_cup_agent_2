import os
import time
import logging
from dotenv import load_dotenv
from src.scraper.twitter_scraper import get_latest_photo_tweet, download_image
from src.telegram.reporter import send_telegram_photo, send_telegram_message
from src.state_manager import load_state, update_post_status, generate_content_id

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_agent_1():
    logging.info("Starting Agent 1: Downloader")
    # Supports multiple profiles separated by comma
    profiles_str = os.getenv("TWITTER_SOURCE_PROFILE", "WorldCupMedia_,Waleedahmdd,FIFAWC26Updates,FIFAcom,SkyFootball,TheSunFootball,footballontnt,TrollFootball,Footballtweet,FBAwayDays")
    profiles = [p.strip() for p in profiles_str.split(',') if p.strip()]
    
    state = load_state()
    # Collect processed URLs by inspecting the state values
    processed = {data.get("source_url") for data in state.values() if data.get("source_url")}
    
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
        
    if tweet.get("status") == "SKIPPED":
        reason = tweet.get("reason", "Unknown Reason")
        checked_profiles = tweet.get("checked_profiles", [])
        
        profiles_list = "\n".join([f"* {p}" for p in checked_profiles])
        
        msg = (
            f"Status: SKIPPED\n\n"
            f"Reason: {reason}\n\n"
            f"Checked Profiles:\n"
            f"{profiles_list}\n\n"
            f"Time Window Checked:\n"
            f"Last 2 Hours"
        )
        
        logging.info(f"Skipped Download: {reason}")
        send_telegram_message(msg)
        return
        
    logging.info(f"Processing new photo tweet: {tweet['url']} from {tweet['profile']}")
    
    content_id = generate_content_id()
    download_path = f"output/{content_id}_raw.jpg"
    
    if download_image(tweet['image_url'], download_path):
        github_run_id = os.getenv('GITHUB_RUN_ID', 'manual')
        caption = (
            f"✅ Download Successfully Completed\n"
            f"🆔 Content ID: {content_id}\n\n"
            f"🎬 Photo Name:\n{tweet['title'][:100]}\n\n"
            f"📥 Download Status: Success\n\n"
            f"🔗 Source URL:\n{tweet['url']}\n\n"
            f"Original File: {content_id}_raw.jpg\n\n"
            f"🕒 Download Time:\n{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n"
            f"📦 GitHub Repository:\nhttps://github.com/Vikram-Bosak/Fifa_world_cup_agent_2\n\n"
            f"📄 Workflow Run:\nhttps://github.com/Vikram-Bosak/Fifa_world_cup_agent_2/actions/runs/{github_run_id}"
        )
        res = send_telegram_photo(download_path, caption)
        if res and res.get("ok"):
            msg_id = str(res['result']['message_id'])
            # Extract highest res photo file_id
            photos = res['result'].get('photo', [])
            file_id = photos[-1]['file_id'] if photos else None
            
            logging.info(f"Sent DOWNLOADED status to Telegram. Content ID: {content_id}, Message ID: {msg_id}")
            
            update_post_status(
                content_id=content_id,
                status="DOWNLOADED",
                source_url=tweet['url'],
                telegram_msg_id=msg_id,
                telegram_file_id=file_id,
                title=tweet['title'],
                profile=tweet['profile'],
                caption=tweet.get('caption', '')
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
