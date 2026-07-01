import os
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from pilmoji import Pilmoji
import logging
import cv2
import numpy as np
import random
import textwrap

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ═══════════════════════════════════════════════════════════════════
# FIFA AGENT 2 - Image Editor (Matching Agent 1 Video Style)
# ═══════════════════════════════════════════════════════════════════

def get_font(size, bold=False):
    """Get DejaVu font (matching Agent 1 style)."""
    if bold:
        font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    else:
        font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    try:
        return ImageFont.truetype(font_path, size)
    except Exception:
        return ImageFont.load_default()

def detect_face_and_crop(img, target_w, target_h):
    """Detect face and smart crop image."""
    img_cv = np.array(img)
    if len(img_cv.shape) == 3 and img_cv.shape[2] == 3:
        gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_cv
        
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
    
    img_w, img_h = img.size
    if len(faces) > 0:
        (x, y, w, h) = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)[0]
        face_center_x = x + w // 2
        face_center_y = y + h // 2
        logging.info("Face detected! Using smart crop.")
    else:
        face_center_x = img_w // 2
        face_center_y = img_h // 2
        logging.info("No face detected. Using center crop.")
        
    ratio = max(target_w / img_w, target_h / img_h)
    new_w = int(img_w * ratio)
    new_h = int(img_h * ratio)
    img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    new_face_center_x = int(face_center_x * ratio)
    new_face_center_y = int(face_center_y * ratio)
    
    left = max(0, new_face_center_x - target_w // 2)
    if left + target_w > new_w: left = new_w - target_w
    
    top = max(0, new_face_center_y - int(target_h * 0.4))
    if top + target_h > new_h: top = new_h - target_h
    
    return img_resized.crop((left, top, left + target_w, top + target_h))

def create_football_post(image_path, output_path, headline, hook_text, branding="FIFA Insider USA", style="News Style", logo_path=None):
    """
    Create Facebook-style image post matching Agent 1's video overlay style.
    Uses: DejaVu fonts, Facebook blue, white text, yellow border, engagement bar.
    """
    # Parse hashtags and description
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

    random_likes = random.randint(10000, 99999)
    likes = f"{random_likes:,}"

    # ═══ Colors (Matching Agent 1) ═══
    fb_blue = (59, 89, 152)
    white = (255, 255, 255)
    yellow = (255, 215, 0)
    line_color = (255, 255, 255, 60)
    black = (0, 0, 0)
    hashtag_color = (160, 176, 192)

    # ═══ Canvas: 1080x1440 (3:4 Facebook format) ═══
    width, height = 1080, 1440
    img = Image.new('RGB', (width, height), black)
    draw = ImageDraw.Draw(img)

    # ═══ 1. Outer Yellow Border (5px) - Agent 1 style ═══
    draw.rectangle([0, 0, width-1, height-1], outline=yellow, width=5)

    # ═══ 2. Top Banner (Facebook Blue) ═══
    top_bar_height = 90
    draw.rectangle([5, 5, width-5, top_bar_height+5], fill=fb_blue)
    
    # Logo
    text_x_pos = 30
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            lw, lh = logo.size
            n_h = 70
            n_w = int(lw * (n_h/lh))
            logo = logo.resize((n_w, n_h), Image.Resampling.LANCZOS)
            img.paste(logo, (15, 10), logo)
            text_x_pos = 15 + n_w + 15
        except Exception as e:
            logging.error(f"Failed to load logo: {e}")

    # Branding text in top banner
    f_brand = get_font(35, bold=True)
    draw.text((text_x_pos, 25), branding, fill=white, font=f_brand)

    # ═══ 3. Main Image Area (below top bar, above bottom bar) ═══
    bottom_bar_height = 340
    image_top = top_bar_height + 10
    image_height = height - bottom_bar_height - image_top - 10
    
    try:
        if image_path.startswith("http"):
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(image_path, headers=headers, timeout=10)
            r.raise_for_status()
            main_img = Image.open(BytesIO(r.content)).convert('RGB')
        else:
            main_img = Image.open(image_path).convert('RGB')
    except Exception as e:
        logging.error(f"Error loading image, using placeholder: {e}")
        main_img = Image.new('RGB', (width-10, image_height), color="#222222")
        
    # Smart crop
    main_img = detect_face_and_crop(main_img, width-10, image_height)
    img.paste(main_img, (5, image_top))

    # ═══ 4. Bottom Banner (Facebook Blue) - Agent 1 style ═══
    bottom_y = height - bottom_bar_height - 5
    draw.rectangle([5, bottom_y, width-5, height-5], fill=fb_blue)

    # ═══ 5. Text Content (White text on blue - Agent 1 style) ═══
    with Pilmoji(img) as pilmoji:
        start_y = bottom_y + 20
        
        # --- SHORT Headline (White, Bold, BIG size 44) ---
        f_head = get_font(44, bold=True)
        headline_text = headline.strip() if headline else "FOOTBALL UPDATE"
        
        # FORCE SHORT: max 6 words ONLY
        headline_words = headline_text.split()[:6]
        headline_text = " ".join(headline_words).upper()
        
        # Single line - no wrapping for headline
        pilmoji.text((30, start_y), headline_text, fill=white, font=f_head)
        start_y += 55
        
        start_y += 8
        
        # --- SHORT Description (White, Regular, size 26) ---
        f_desc = get_font(26, bold=False)
        
        # FORCE SHORT: max 18 words, 2 lines
        desc_words = description.split()[:18]
        short_description = " ".join(desc_words)
        if len(description.split()) > 18:
            short_description += "..."
        
        story_lines = textwrap.wrap(short_description, width=70)
        for line in story_lines[:2]:  # Max 2 lines ONLY
            pilmoji.text((30, start_y), line, fill=white, font=f_desc)
            start_y += 34
        
        start_y += 5
        
        # --- Hashtags (Light Gray, size 26) ---
        f_tags = get_font(26, bold=False)
        if hashtag_str:
            # Limit hashtags to max 5
            tag_list = hashtag_str.split()[:5]
            hashtag_str = " ".join(tag_list)
            pilmoji.text((30, start_y), hashtag_str, fill=hashtag_color, font=f_tags)
            start_y += 40
        
        # --- Separator Line ---
        sep_y = height - 100
        draw.line([(25, sep_y), (width - 25, sep_y)], fill=line_color, width=2)
        
        # --- "Tap or hold..." Hint Text ---
        f_hint = get_font(22, bold=False)
        hint_text = "Tap or hold to like and react with Love, Haha, Wow, or Sad!"
        hint_bbox = draw.textbbox((0, 0), hint_text, font=f_hint)
        hint_w = hint_bbox[2] - hint_bbox[0]
        draw.text((width - hint_w - 30, sep_y - 35), hint_text, fill=(200, 200, 200), font=f_hint)
        
        # --- ENGAGEMENT BAR (Agent 1 style with colored circles) ---
        engage_y = height - 80
        f_stats = get_font(35, bold=True)
        
        # Overlapping emoji circles (Facebook style)
        draw.ellipse([30, engage_y, 70, engage_y+40], fill=(24,119,242))
        draw.ellipse([55, engage_y, 95, engage_y+40], fill=(240,40,73))
        draw.ellipse([80, engage_y, 120, engage_y+40], fill=(247,177,37))
        draw.ellipse([105, engage_y, 145, engage_y+40], fill=(247,177,37))
        
        pilmoji.text((35, engage_y+2), "👍", fill=white, font=f_stats)
        pilmoji.text((60, engage_y+2), "❤️", fill=white, font=f_stats)
        pilmoji.text((85, engage_y+2), "😂", fill=white, font=f_stats)
        pilmoji.text((110, engage_y+2), "😲", fill=white, font=f_stats)
        
        pilmoji.text((160, engage_y+2), f"{likes} Likes", fill=white, font=f_stats)
        pilmoji.text((500, engage_y+2), "💬 Comment", fill=white, font=f_stats)
        pilmoji.text((780, engage_y+2), "↗️ Share", fill=white, font=f_stats)

    # ═══ 6. Video/Image Credit (with shadow - Agent 1 style) ═══
    f_credit = get_font(30, bold=True)
    credit_text = "Photo Credit: Twitter (X)"
    credit_bbox = draw.textbbox((0, 0), credit_text, font=f_credit)
    credit_w = credit_bbox[2] - credit_bbox[0]
    credit_x = width - credit_w - 30
    credit_y = bottom_y - 45
    
    # Shadow effect
    for offset in [(2,2), (-2,-2), (2,-2), (-2,2), (0,2), (2,0), (-2,0), (0,-2)]:
        draw.text((credit_x + offset[0], credit_y + offset[1]), credit_text, fill=(0, 0, 0), font=f_credit)
    draw.text((credit_x, credit_y), credit_text, fill=(230, 230, 230), font=f_credit)

    # ═══ Save ═══
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    img.save(output_path, quality=95)
    logging.info(f"Image saved to {output_path} with Agent 1 style overlay.")
    return True

if __name__ == "__main__":
    logging.info("Image processor module loaded. Use create_football_post() to generate posters.")
