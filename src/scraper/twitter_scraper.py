import os
import requests
import feedparser
from bs4 import BeautifulSoup
import logging
import random
import time
import calendar
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.cz",
    "https://nitter.fdn.fr",
    "https://nitter.1d4.us",
    "https://nitter.kavin.rocks"
]

def get_latest_photo_tweet(profiles, processed_urls):
    """
    Scans multiple profiles and returns the latest UNPROCESSED PHOTO tweet.
    Ensures that Videos and GIFs are strictly ignored.
    Also ensures the tweet is from the last 2 hours.
    """
    random.shuffle(NITTER_INSTANCES)
    
    # We will collect all valid photo tweets across profiles, then sort by date if possible,
    # or just return the first valid one we find.
    valid_tweets = []
    
    for instance in NITTER_INSTANCES:
        success_on_instance = False
        
        for profile in profiles:
            rss_url = f"{instance}/{profile.strip()}/rss"
            logging.info(f"Scanning profile: {profile} via {rss_url}")
            
            try:
                from src.http_client import get_retry_session
                session = get_retry_session(retries=3)
                resp = session.get(rss_url, timeout=10)
                resp.raise_for_status()
                feed = feedparser.parse(resp.content)
                
                if not feed.entries:
                    continue
                    
                success_on_instance = True
                
                for entry in feed.entries:
                    link = entry.link
                    
                    if link in processed_urls:
                        continue # Skip already processed
                        
                    # Check if tweet is within the last 2 hours (7200 seconds)
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_ts = calendar.timegm(entry.published_parsed)
                        age_seconds = time.time() - pub_ts
                        if age_seconds > 7200:
                            logging.info(f"Skipping {link} - Older than 2 hours (Age: {int(age_seconds/60)} mins)")
                            continue
                            
                    title = entry.title
                    description = entry.description
                    
                    # Check for video/gif indicators in the description
                    if '>Video<' in description or '>GIF<' in description or 'video_thumb' in description:
                        logging.info(f"Skipping {link} - Contains Video/GIF")
                        continue
                        
                    soup = BeautifulSoup(description, 'html.parser')
                    
                    # Additional check for video tags just in case
                    if soup.find('video') or 'video.twimg.com' in description or 'tweet-video' in description:
                        logging.info(f"Skipping {link} - Contains Video/GIF")
                        continue
                        
                    # Find images
                    img_tags = soup.find_all('img')
                    valid_image_url = None
                    
                    for img in img_tags:
                        img_url = img.get('src')
                        # Filter out profile pictures, emojis, or small icons
                        if img_url and 'profile_images' not in img_url and 'emoji' not in img_url:
                            valid_image_url = f"{instance}{img_url}" if img_url.startswith('/') else img_url
                            break
                            
                    # Extract clean text caption
                    clean_text = soup.get_text(separator=' ', strip=True)
                    p_tag = soup.find('p')
                    if p_tag:
                        clean_text = p_tag.get_text(separator=' ', strip=True)
                        
                    if valid_image_url:
                        # Found a valid photo tweet
                        valid_tweets.append({
                            "title": title,
                            "caption": clean_text,
                            "url": link,
                            "image_url": valid_image_url,
                            "profile": profile
                        })
                        
            except Exception as e:
                logging.error(f"Error fetching from {rss_url}: {e}")
                continue
                
        if success_on_instance and valid_tweets:
            # We got some valid tweets, return the first one (most recent usually)
            return valid_tweets[0]
            
    logging.warning("Could not fetch a valid new photo tweet from any profile/instance.")
    return None

def download_image(url, output_path):
    from src.http_client import get_retry_session
    try:
        session = get_retry_session(retries=3)
        response = session.get(url, timeout=15)
        response.raise_for_status()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(response.content)
        return True
    except Exception as e:
        logging.error(f"Failed to download image from {url}: {e}")
        return False
