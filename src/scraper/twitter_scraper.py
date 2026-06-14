import os
import time
import logging
import random
import asyncio
from datetime import datetime, timezone
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_latest_photo_tweet(profiles, processed_urls):
    return asyncio.run(_get_latest_photo_tweet_async(profiles, processed_urls))

async def _get_latest_photo_tweet_async(profiles, processed_urls):
    try:
        from twikit import Client
        from twikit.user import User
        # Monkeypatch User.__init__ to fix 'urls' KeyError in twikit==2.1.2
        if not hasattr(User, '_patched_for_urls'):
            orig_init = User.__init__
            def patched_init(self, client, data):
                if 'legacy' in data:
                    legacy = data['legacy']
                    # Patch all potential missing keys in legacy
                    defaults = {
                        'location': '',
                        'description': '',
                        'pinned_tweet_ids_str': [],
                        'verified': False,
                        'possibly_sensitive': False,
                        'can_dm': False,
                        'can_media_tag': False,
                        'want_retweets': False,
                        'default_profile': False,
                        'default_profile_image': False,
                        'has_custom_timelines': False,
                        'followers_count': 0,
                        'fast_followers_count': 0,
                        'normal_followers_count': 0,
                        'friends_count': 0,
                        'favourites_count': 0,
                        'listed_count': 0,
                        'media_count': 0,
                        'statuses_count': 0,
                        'is_translator': False,
                        'translator_type': '',
                        'withheld_in_countries': []
                    }
                    for k, v in defaults.items():
                        if k not in legacy:
                            legacy[k] = v
                            
                    if 'entities' in legacy:
                        entities = legacy['entities']
                        if 'description' in entities and 'urls' not in entities['description']:
                            entities['description']['urls'] = []
                        if 'url' in entities and 'urls' not in entities['url']:
                            if 'url' not in entities:
                                entities['url'] = {}
                            entities['url']['urls'] = []
                orig_init(self, client, data)
            User.__init__ = patched_init
            User._patched_for_urls = True
    except ImportError:
        logging.error("twikit is not installed. Run: pip install twikit")
        return None
        
    client = Client('en-US')
    
    # Check credentials
    username = os.getenv("TWITTER_USERNAME")
    email = os.getenv("TWITTER_EMAIL")
    password = os.getenv("TWITTER_PASSWORD")
    
    # Try to load cookies
    cookies_path = 'cookies.json'
    try:
        if os.path.exists(cookies_path):
            client.load_cookies(cookies_path)
            logging.info("Loaded Twitter cookies.")
        else:
            if not all([username, email, password]):
                logging.error("Missing Twitter credentials in .env and no cookies.json found.")
                return None
            logging.info("Logging into Twitter...")
            await client.login(auth_info_1=username, auth_info_2=email, password=password)
            client.save_cookies(cookies_path)
            logging.info("Successfully logged in and saved cookies.")
    except Exception as e:
        logging.error(f"Twitter Authentication failed: {e}")
        return None
        
    found_any_in_2h = False
    found_duplicate_in_2h = False
    
    for profile in profiles:
        logging.info(f"Scanning profile: {profile} via twikit")
        try:
            user = await client.get_user_by_screen_name(profile.strip())
            tweets = await user.get_tweets('Tweets', count=10)
            
            for tweet in tweets:
                # Check age (within last 2 hours)
                try:
                    pub_time = datetime.strptime(tweet.created_at, '%a %b %d %H:%M:%S %z %Y')
                    age_seconds = (datetime.now(timezone.utc) - pub_time).total_seconds()
                    if age_seconds > 7200:
                        continue
                    found_any_in_2h = True
                except Exception as e:
                    logging.warning(f"Could not parse tweet time: {tweet.created_at} - {e}")
                    pass
                
                # Construct tweet URL
                url = f"https://x.com/{profile.strip()}/status/{tweet.id}"
                
                if url in processed_urls:
                    found_duplicate_in_2h = True
                    continue
                    
                text = tweet.text
                
                # Check for video/gif indicators in text
                if '>Video<' in text or '>GIF<' in text:
                    continue
                    
                # Check media
                if not hasattr(tweet, 'media') or not tweet.media:
                    continue
                    
                has_video = False
                valid_image_url = None
                
                for m in tweet.media:
                    if m['type'] in ['video', 'animated_gif']:
                        has_video = True
                        break
                    if m['type'] == 'photo' and not valid_image_url:
                        valid_image_url = m['media_url_https']
                        
                if has_video or not valid_image_url:
                    continue
                    
                # Found a valid tweet
                logging.info(f"Found valid tweet from {profile}. Stopping scan.")
                return {
                    "title": text[:100].replace('\n', ' '), # Safe title
                    "caption": text,
                    "url": url,
                    "image_url": valid_image_url,
                    "profile": profile
                }
                
        except Exception as e:
            logging.error(f"Error fetching tweets for {profile}: {e}")
            await asyncio.sleep(2)
            continue
            
    # If we get here, no unprocessed valid tweet was found
    if found_duplicate_in_2h:
        return {
            "status": "SKIPPED",
            "reason": "Content already processed.",
            "checked_profiles": profiles
        }
    
    return {
        "status": "SKIPPED",
        "reason": "No valid image found in the last 2 hours across all configured Twitter profiles.",
        "checked_profiles": profiles
    }

def download_image(url, output_path):
    import requests
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
