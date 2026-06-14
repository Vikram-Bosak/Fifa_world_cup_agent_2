import os
import requests
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def ensure_font_downloaded(font_url, font_path):
    os.makedirs(os.path.dirname(font_path), exist_ok=True)
    if not os.path.exists(font_path):
        try:
            logging.info(f"Downloading font from {font_url}")
            r = requests.get(font_url, timeout=10)
            with open(font_path, 'wb') as f:
                f.write(r.content)
        except Exception as e:
            logging.error(f"Failed to download font: {e}")

def get_font(size):
    font_path = "assets/fonts/Roboto-Bold.ttf"
    font_url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
    ensure_font_downloaded(font_url, font_path)
    try:
        return ImageFont.truetype(font_path, size)
    except Exception:
        return ImageFont.load_default()

def draw_gradient_overlay(img):
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = img.size
    gradient_start_y = int(height * 0.3) 
    
    for y in range(gradient_start_y, height):
        opacity = int(255 * ((y - gradient_start_y) / (height - gradient_start_y)))
        draw.line([(0, y), (width, y)], fill=(0, 0, 0, opacity))
        
    img.paste(overlay, (0, 0), overlay)

def create_football_post(image_path, output_path, headline, hook_text, branding="FIFAWorldCup USA", style="Breaking News Style", logo_path=None):
    try:
        img = Image.open(image_path)
    except Exception as e:
        logging.error(f"Error opening image {image_path}: {e}")
        return False

    img = img.convert('RGB')
    
    # 1080x1350 (4:5) crop and resize
    width, height = img.size
    target_ratio = 1080 / 1350.0
    current_ratio = width / height
    
    if current_ratio > target_ratio:
        # Image is too wide
        new_width = int(height * target_ratio)
        left = (width - new_width) / 2
        right = left + new_width
        top = 0
        bottom = height
    else:
        # Image is too tall
        new_height = int(width / target_ratio)
        top = (height - new_height) / 2
        bottom = top + new_height
        left = 0
        right = width
        
    img = img.crop((left, top, right, bottom))
    img = img.resize((1080, 1350), Image.Resampling.LANCZOS)
    
    # Emotional/Sad Style: Desaturate the image
    if style in ["Emotional Style", "Sad Style"]:
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(0.4)
        enhancer_brightness = ImageEnhance.Brightness(img)
        img = enhancer_brightness.enhance(0.8)

    draw = ImageDraw.Draw(img)
    
    main_font = get_font(56)
    hook_font = get_font(40)
    brand_font = get_font(30)
    
    from pilmoji import Pilmoji
    def get_lines(text, font, max_w):
        with Pilmoji(img) as pilmoji:
            words = text.split()
            lines, current_line = [], []
            for word in words:
                test_line = current_line + [word]
                clean_text = " ".join(test_line).replace('*', '')
                line_width, _ = pilmoji.getsize(clean_text, font=font)
                if line_width <= max_w:
                    current_line.append(word)
                else:
                    if current_line: lines.append(current_line)
                    current_line = [word]
            if current_line: lines.append(current_line)
            return lines

    def draw_text_with_outline(lines, font, y_pos, line_height, text_color, outline_color, stroke_width=3, center=True, is_impact=False):
        with Pilmoji(img) as pilmoji:
            for line_words in lines:
                clean_line = " ".join(line_words).replace('*', '')
                line_width, _ = pilmoji.getsize(clean_line, font=font)
                x = (1080 - line_width) / 2 if center else 60
                
                is_highlight = False
                for i, word in enumerate(line_words):
                    if word.startswith('*'):
                        is_highlight = True
                        word = word[1:]
                    end_highlight = False
                    if word.endswith('*'):
                        end_highlight = True
                        word = word[:-1]
                        
                    current_color = "#FFD700" if is_highlight and not is_impact else text_color
                    if is_impact:
                        current_color = "#FFD700"
                        outline_color = "#000000"
                    
                    # Draw Outline
                    if outline_color:
                        pilmoji.text((x-stroke_width, y_pos-stroke_width), word, font=font, fill=outline_color)
                        pilmoji.text((x+stroke_width, y_pos-stroke_width), word, font=font, fill=outline_color)
                        pilmoji.text((x-stroke_width, y_pos+stroke_width), word, font=font, fill=outline_color)
                        pilmoji.text((x+stroke_width, y_pos+stroke_width), word, font=font, fill=outline_color)
                    
                    pilmoji.text((x, y_pos), word, font=font, fill=current_color)
                    
                    word_width, _ = pilmoji.getsize(word, font=font)
                    x += word_width
                    if end_highlight: is_highlight = False
                    if i < len(line_words) - 1:
                        space_width, _ = pilmoji.getsize(" ", font=font)
                        x += space_width
                y_pos += line_height
            return y_pos

    # Shorten the hook text if it's too long
    if len(hook_text) > 150:
        hook_text = hook_text[:147] + "..."

    # Apply Style Logic
    if style in ["Meme Style", "Comparison Style"]:
        headline_lines = get_lines(headline, main_font, 960)
        hook_lines = get_lines(hook_text, hook_font, 960)
        
        # Impact Meme Style Layout
        draw_text_with_outline(headline_lines, main_font, 80, 60, "#FFD700", "#000000", stroke_width=4, is_impact=True)
        draw_text_with_outline(hook_lines, hook_font, 1350 - 150 - (len(hook_lines) * 45), 45, "#FFFFFF", "#000000", stroke_width=3)
        
    elif style in ["Emotional Style", "Sad Style", "Storytelling Style"]:
        # Heavy Bottom Gradient
        draw_gradient_overlay(img)
        headline_lines = get_lines(headline, main_font, 960)
        hook_lines = get_lines(hook_text, hook_font, 960)
        
        total_h = (len(headline_lines) * 60) + (len(hook_lines) * 45) + 40
        start_y = 1350 - 150 - total_h
        
        start_y = draw_text_with_outline(headline_lines, main_font, start_y, 60, "#FFFFFF", None, center=False)
        start_y += 20
        draw_text_with_outline(hook_lines, hook_font, start_y, 45, "#CCCCCC", None, center=False)
        
    else: # Breaking News Style (Default)
        headline_lines = get_lines(headline, main_font, 960)
        headline_h = len(headline_lines) * 60 + 60
        
        # Top Yellow Banner
        draw.rectangle([0, 0, 1080, headline_h], fill="#FFD700")
        draw_text_with_outline(headline_lines, main_font, 30, 60, "#000000", None)
        
        hook_lines = get_lines(hook_text, hook_font, 960)
        hook_h = len(hook_lines) * 45 + 60
        
        # Bottom Black Banner
        draw.rectangle([0, 1350 - hook_h - 100, 1080, 1350], fill="#000000")
        draw_text_with_outline(hook_lines, hook_font, 1350 - hook_h - 70, 45, "#FFFFFF", None)

    # Branding Logo (Top Right Corner with Opacity)
    try:
        if logo_path and os.path.exists(logo_path):
            logo = Image.open(logo_path).convert("RGBA")
            # Auto-scale: ~12% of image width
            target_w = int(1080 * 0.12)
            logo.thumbnail((target_w, target_w), Image.Resampling.LANCZOS)
            
            # Opacity ~90%
            alpha = logo.split()[3]
            alpha = ImageEnhance.Brightness(alpha).enhance(0.9)
            logo.putalpha(alpha)
            
            # Top Right Position with safe margin
            margin_x = 40
            margin_y = 40
            
            x_pos = 1080 - logo.width - margin_x
            y_pos = margin_y
            
            img.paste(logo, (x_pos, y_pos), logo)
            
        # Draw branding text at bottom left
        draw.text((40, 1350 - 60), branding, font=brand_font, fill=(200, 200, 200))
    except Exception as e:
        logging.error(f"Error placing logo: {e}")
        draw.text((40, 1350 - 60), branding, font=brand_font, fill=(200, 200, 200))
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "JPEG", quality=95)
    logging.info(f"Image saved to {output_path} with style: {style}")
    return True
