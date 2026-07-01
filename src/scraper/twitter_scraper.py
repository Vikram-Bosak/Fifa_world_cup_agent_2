import os
import time
import logging
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Nitter instances (fallback order)
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://xcancel.com",
]

def _fetch_rss(url, timeout=15):
    """Fetch RSS feed from URL."""
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    resp = urllib.request.urlopen(req, timeout=timeout)
    return resp.read().decode('utf-8', errors='replace')

def _find_working_nitter():
    """Find a working Nitter instance."""
    for instance in NITTER_INSTANCES:
        try:
            url = f"{instance}/FIFAcom/rss"
            _fetch_rss(url, timeout=10)
            logging.info(f"Using Nitter instance: {instance}")
            return instance
        except Exception:
            continue
    logging.warning("No working Nitter instance found. Trying xcancel.com as last resort.")
    return "https://xcancel.com"

def _parse_rss_date(date_str):
    """Parse RSS date string to datetime."""
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        try:
            # Try ISO format
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except Exception:
            return None

def get_latest_photo_tweet(profiles, processed_urls):
    """
    Find latest photo tweet from Twitter profiles using Nitter RSS.
    Returns dict with tweet info or SKIPPED status.
    """
    logging.info(f"Searching Nitter RSS for photos from {len(profiles)} profiles...")
    
    nitter = _find_working_nitter()
    time_limit = datetime.now(timezone.utc) - timedelta(hours=3)
    
    for profile in profiles:
        profile = profile.strip()
        if not profile:
            continue
            
        logging.info(f"Checking profile: {profile}")
        
        try:
            rss_url = f"{nitter}/{profile}/rss"
            rss_data = _fetch_rss(rss_url)
            
            # Parse RSS
            root = ET.fromstring(rss_data)
            
            for item in root.findall('.//item'):
                # Get tweet URL
                link = item.find('link')
                if link is None or not link.text:
                    continue
                tweet_url = link.text.strip()
                
                # Skip if already processed
                if tweet_url in processed_urls:
                    continue
                
                # Get publication date
                pub_date_el = item.find('pubDate')
                if pub_date_el is not None and pub_date_el.text:
                    pub_date = _parse_rss_date(pub_date_el.text)
                    if pub_date:
                        # Make timezone-aware if naive
                        if pub_date.tzinfo is None:
                            pub_date = pub_date.replace(tzinfo=timezone.utc)
                        if pub_date < time_limit:
                            continue  # Too old
                
                # Get title/description
                title_el = item.find('title')
                title = title_el.text.strip() if title_el is not None and title_el.text else ""
                
                desc_el = item.find('description')
                description = desc_el.text.strip() if desc_el is not None and desc_el.text else ""
                
                # Check if this is a video (skip videos)
                content = (title + " " + description).lower()
                if 'video' in content or '>video<' in content or '>gif<' in content:
                    logging.debug(f"Skipping video tweet: {tweet_url}")
                    continue
                
                # Extract image URL from description (Nitter embeds images as <img> tags)
                image_url = None
                if '<img' in description:
                    # Parse HTML to find img src
                    try:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(description, 'html.parser')
                        img_tag = soup.find('img')
                        if img_tag and img_tag.get('src'):
                            src = img_tag['src']
                            # Convert Nitter URL to direct image URL
                            if src.startswith('/pic/'):
                                src = f"{nitter}{src}"
                            elif src.startswith('http'):
                                pass  # Already absolute
                            else:
                                src = f"{nitter}/{src}"
                            image_url = src
                    except Exception as e:
                        logging.debug(f"Failed to parse image from HTML: {e}")
                
                # Also check media:thumbnail in RSS
                if not image_url:
                    media_thumb = item.find('{http://search.yahoo.com/mrss/}thumbnail')
                    if media_thumb is not None:
                        image_url = media_thumb.get('url')
                
                # Check enclosure
                if not image_url:
                    enclosure = item.find('enclosure')
                    if enclosure is not None and 'image' in enclosure.get('type', ''):
                        image_url = enclosure.get('url')
                
                if not image_url:
                    logging.debug(f"No image found in tweet: {tweet_url}")
                    continue
                
                # Make image URL absolute if needed
                if image_url.startswith('/'):
                    image_url = f"{nitter}{image_url}"
                
                logging.info(f"Found photo from {profile}: {tweet_url}")
                
                return {
                    "title": title[:100].replace('\n', ' '),
                    "caption": description or title,
                    "url": tweet_url,
                    "image_url": image_url,
                    "profile": profile,
                    "status": "FOUND"
                }
                
        except Exception as e:
            logging.error(f"Error fetching RSS for {profile}: {e}")
            continue
    
    return {
        "status": "SKIPPED",
        "reason": "No new photo found in the last 3 hours across all profiles.",
        "checked_profiles": profiles
    }

def download_image(url, output_path):
    """Download image from URL to output_path."""
    import requests
    from src.http_client import get_retry_session
    try:
        session = get_retry_session(retries=3)
        response = session.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(response.content)
        logging.info(f"Downloaded image: {output_path} ({len(response.content)} bytes)")
        return True
    except Exception as e:
        logging.error(f"Failed to download image from {url}: {e}")
        return False
