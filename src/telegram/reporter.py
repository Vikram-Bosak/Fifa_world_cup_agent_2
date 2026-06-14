import os
import logging
from src.http_client import get_retry_session

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def send_telegram_message(text, reply_to_message_id=None):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        logging.error("Telegram credentials missing.")
        return None
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    if reply_to_message_id:
        data['reply_to_message_id'] = reply_to_message_id
        
    try:
        session = get_retry_session(retries=3)
        response = session.post(url, data=data, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Failed to send message: {e}")
        return None

def send_telegram_report_message(text, reply_to_message_id=None):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_REPORT_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        logging.error("Telegram report credentials missing. Please set TELEGRAM_REPORT_CHAT_ID in .env.")
        return None
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    if reply_to_message_id:
        data['reply_to_message_id'] = reply_to_message_id
        
    try:
        session = get_retry_session(retries=3)
        response = session.post(url, data=data, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Failed to send report message: {e}")
        return None

def send_telegram_photo(photo_path, caption, reply_to_message_id=None):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        logging.error("Telegram credentials missing.")
        return None
        
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    data = {
        'chat_id': chat_id,
        'caption': caption,
        'parse_mode': 'HTML'
    }
    if reply_to_message_id:
        data['reply_to_message_id'] = reply_to_message_id
        
    try:
        session = get_retry_session(retries=3)
        with open(photo_path, 'rb') as photo:
            files = {'photo': photo}
            response = session.post(url, data=data, files=files, timeout=30)
            response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Failed to send photo: {e}")
        return None

def download_telegram_photo(file_id, output_path):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logging.error("Telegram bot token missing.")
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
    try:
        session = get_retry_session(retries=3)
        response = session.get(url, timeout=15)
        response.raise_for_status()
        
        file_path = response.json()['result']['file_path']
        download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        
        img_resp = session.get(download_url, timeout=30)
        img_resp.raise_for_status()
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'wb') as handler:
            handler.write(img_resp.content)
            
        logging.info(f"Downloaded image to {output_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to download telegram photo: {e}")
        return False

