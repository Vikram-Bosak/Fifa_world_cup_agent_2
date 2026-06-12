import os
import requests
import logging

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
        
    response = requests.post(url, data=data)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Failed to send message: {response.text}")
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
        
    with open(photo_path, 'rb') as photo:
        files = {'photo': photo}
        response = requests.post(url, data=data, files=files)
        
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Failed to send photo: {response.text}")
        return None

def download_telegram_photo(file_id, output_path):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logging.error("Telegram bot token missing.")
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
    response = requests.get(url)
    if response.status_code != 200:
        logging.error(f"Failed to get file info: {response.text}")
        return False
        
    file_path = response.json()['result']['file_path']
    download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
    
    img_data = requests.get(download_url).content
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'wb') as handler:
        handler.write(img_data)
        
    logging.info(f"Downloaded image to {output_path}")
    return True
