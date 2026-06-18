import os
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from pilmoji import Pilmoji
import logging
import cv2
import numpy as np
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def ensure_font_downloaded(font_url, font_path):
    if not os.path.exists(font_path):
        try:
            r = requests.get(font_url, timeout=10)
            with open(font_path, 'wb') as f:
                f.write(r.content)
        except Exception as e:
            logging.error(f"Failed to download font: {e}")

def get_font(size, bold=False):
    os.makedirs("assets/fonts", exist_ok=True)
    if bold:
        font_path = "assets/fonts/Roboto-Bold.ttf"
        font_url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
    else:
        font_path = "assets/fonts/Roboto-Regular.ttf"
        font_url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf"
        
    ensure_font_downloaded(font_url, font_path)
    try:
        return ImageFont.truetype(font_path, size)
    except Exception:
        return ImageFont.load_default()

def detect_face_and_crop(img, target_w, target_h):
    """
    Detects a face in the image and crops it so the face is always in the safe zone.
    """
    img_cv = np.array(img)
    if len(img_cv.shape) == 3 and img_cv.shape[2] == 3:
        gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_cv
        
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
    
    img_w, img_h = img.size
    if len(faces) > 0:
        # Get largest face
        (x, y, w, h) = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)[0]
        face_center_x = x + w // 2
        face_center_y = y + h // 2
        logging.info("Face detected! Using smart crop.")
    else:
        face_center_x = img_w // 2
        face_center_y = img_h // 2
        logging.info("No face detected. Using center crop.")
        
    # Resize image so the smallest dimension matches the target
    ratio = max(target_w / img_w, target_h / img_h)
    new_w = int(img_w * ratio)
    new_h = int(img_h * ratio)
    img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Map face center to new dimensions
    new_face_center_x = int(face_center_x * ratio)
    new_face_center_y = int(face_center_y * ratio)
    
    # Calculate crop box
    left = max(0, new_face_center_x - target_w // 2)
    if left + target_w > new_w: left = new_w - target_w
    
    # Vertically position face slightly above center for good composition
    top = max(0, new_face_center_y - int(target_h * 0.4))
    if top + target_h > new_h: top = new_h - target_h
    
    return img_resized.crop((left, top, left + target_w, top + target_h))

def create_football_post(image_path, output_path, headline, hook_text, branding="FIFA Insider USA", style="News Style", logo_path=None):
    words = hook_text.split()
    desc_words = []
    hashtags = []
    for w in words:
        if w.startswith('#'):
            hashtags.append(w)
        else:
            desc_words.append(w)
            
    description = " ".join(desc_words)
    hashtag_str = " ".join(hashtags)
    if not hashtag_str:
        hashtag_str = "#FIFAWorldCup #Football #Soccer"

    random_likes = random.randint(5420, 29850)
    likes = f"{random_likes:,}"

    # Strict 80/20 Layout
    # Content: 1060x1420
    # Header: 110px
    # Footer: 140px
    # Remaining: 1170px
    # Image: 936px (80%)
    # Text: 234px (20%)

    base_img = Image.new('RGB', (1080, 1440), color="#C6A664")
    content = Image.new('RGB', (1060, 1420), color="#000000") # Black background for text area
    draw = ImageDraw.Draw(content)
    
    header_font = get_font(55, bold=True)
    credit_font = get_font(30, bold=True)
    title_font = get_font(35, bold=True)
    desc_font = get_font(26, bold=True) # Bold description
    small_font = get_font(18, bold=False)
    footer_font = get_font(30, bold=True)
    
    with Pilmoji(content) as pilmoji:
        # 1. Top Header
        draw.rectangle([0, 0, 1060, 110], fill="#1E243A")
        
        text_x_pos = 30
        if logo_path and os.path.exists(logo_path):
            try:
                logo = Image.open(logo_path).convert("RGBA")
                lw, lh = logo.size
                n_h = 80
                n_w = int(lw * (n_h/lh))
                logo = logo.resize((n_w, n_h), Image.Resampling.LANCZOS)
                content.paste(logo, (20, 15), logo)
                text_x_pos = 20 + n_w + 20
            except Exception as e:
                logging.error(f"Failed to load logo: {e}")

        header_text = f"{branding}"
        pilmoji.text((text_x_pos, 25), header_text, font=header_font, fill="#FFFFFF")

        # 2. Main Image (Height 936)
        try:
            if image_path.startswith("http"):
                headers = {'User-Agent': 'Mozilla/5.0'}
                r = requests.get(image_path, headers=headers, timeout=10)
                r.raise_for_status()
                main_img = Image.open(BytesIO(r.content)).convert('RGB')
            else:
                main_img = Image.open(image_path).convert('RGB')
        except Exception as e:
            logging.error(f"Error downloading image, using placeholder: {e}")
            main_img = Image.new('RGB', (1060, 936), color="#222222")
            
        # Smart crop using Face Detection
        main_img = detect_face_and_crop(main_img, 1060, 936)
        content.paste(main_img, (0, 110))
        
        # Video Credit
        credit_text = "Video Credit: Twitter (x) videos"
        c_bbox = draw.textbbox((0,0), credit_text, font=credit_font)
        c_w = c_bbox[2] - c_bbox[0]
        draw.text((1060 - c_w - 20 + 2, 110 + 936 - 45 + 2), credit_text, font=credit_font, fill="#000000") # Shadow
        draw.text((1060 - c_w - 20, 110 + 936 - 45), credit_text, font=credit_font, fill="#E0E0E0")
        
        # 3. Text Area (20% -> 234px)
        text_y = 1065
        
        # Title
        pilmoji.text((30, text_y), headline.upper(), font=title_font, fill="#FFFF00") # Yellow text
        text_y += 50
        
        # Description
        lines = []
        current_line = []
        for word in description.split():
            current_line.append(word)
            bbox = draw.textbbox((0,0), " ".join(current_line), font=desc_font)
            if bbox[2] - bbox[0] > 1000:
                current_line.pop()
                lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))
        
        for line in lines[:2]: # Max 2 lines to fit safely
            pilmoji.text((30, text_y), line, font=desc_font, fill="#FFFF00") # Yellow text
            text_y += 35
            
        text_y += 15
        # Hashtags
        pilmoji.text((30, text_y), hashtag_str, font=desc_font, fill="#FFFF00") # Yellow text
        
        # 4. Footer section (1280 to 1420)
        footer_y = 1280
        draw.rectangle([0, footer_y, 1060, 1420], fill="#334168")
        draw.line([(0, footer_y), (1060, footer_y)], fill="#506080", width=2)
        
        tiny_text = "Tap or hold to like and react with Love, Haha, Wow, or Sad!"
        t_bbox = draw.textbbox((0,0), tiny_text, font=small_font)
        draw.text(((1060 - (t_bbox[2]-t_bbox[0]))/2, footer_y + 10), tiny_text, font=small_font, fill="#A0A0A0")
        
        action_y = 1345
        pilmoji.text((30, action_y), f"👍 ❤️ {likes} Likes", font=footer_font, fill="#FFFFFF")
        pilmoji.text((450, action_y), "😂 😲 😢", font=footer_font, fill="#FFFFFF")
        pilmoji.text((650, action_y), "💬 Comment", font=footer_font, fill="#FFFFFF")
        pilmoji.text((880, action_y), "🔗 Share", font=footer_font, fill="#FFFFFF")
        
    base_img.paste(content, (10, 10))
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    base_img.save(output_path)
    logging.info(f"Image saved to {output_path} with smart crop and 80/20 layout.")
    return True

if __name__ == "__main__":
    logging.info("Image processor module loaded. Use create_football_post() to generate posters.")
