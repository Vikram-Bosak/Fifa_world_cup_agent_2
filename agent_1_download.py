import os
import time
import logging
from dotenv import load_dotenv
from src.scraper.twitter_scraper import get_latest_photo_tweet, download_image
from src.telegram.reporter import send_telegram_photo, send_telegram_message

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_processed_tweets():
    if not os.path.exists("output/processed_tweets.txt"):
        return set()
    with open("output/processed_tweets.txt", "r") as f:
        return set(line.strip() for line in f)

def save_processed_tweet(tweet_url):
    os.makedirs("output", exist_ok=True)
    with open("output/processed_tweets.txt", "a") as f:
        f.write(f"{tweet_url}\n")

def run_agent_1():
    logging.info("Starting Agent 1: Downloader")
    # Supports multiple profiles separated by comma
    profiles_str = os.getenv("TWITTER_SOURCE_PROFILE", "FIFAWorldCup,Cristiano")
    profiles = [p.strip() for p in profiles_str.split(',') if p.strip()]
    
    processed = load_processed_tweets()
    
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
            logging.info(f"Sent DOWNLOADED status to Telegram. Message ID: {res['result']['message_id']}")
            save_processed_tweet(tweet['url'])
        else:
            logging.error("Failed to send photo to Telegram.")
    else:
        logging.error("Failed to download image from Twitter.")

if __name__ == "__main__":
    load_dotenv()
    run_agent_1()
