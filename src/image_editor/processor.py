from PIL import Image, ImageDraw, ImageFont, ImageOps
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def add_watermark(image_path, output_path, logo_path=None, watermark_text="FIFA World Cup"):
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGBA")
            
            # Resize and Center Crop to 1080 x 1350 px
            target_size = (1080, 1350)
            img = ImageOps.fit(img, target_size, Image.Resampling.LANCZOS)
            width, height = img.size
            
            # Create a transparent overlay
            overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)
            
            # 1. Facebook Page Logo (Top Left)
            if logo_path and os.path.exists(logo_path):
                try:
                    with Image.open(logo_path) as logo:
                        logo = logo.convert("RGBA")
                        logo_width = int(width * 0.25) # 25% of image width
                        w_percent = (logo_width / float(logo.size[0]))
                        logo_height = int((float(logo.size[1]) * float(w_percent)))
                        logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
                        
                        # Position: top left with 30px padding
                        overlay.paste(logo, (30, 30), logo)
                except Exception as e:
                    logging.warning(f"Could not add logo: {e}")
            
            # 2. Branding Watermark (Top Right)
            brand_text = "@FIFAInsiderUSA"
            try:
                brand_font = ImageFont.truetype("assets/fonts/bold.ttf", int(height * 0.025))
            except IOError:
                try:
                    brand_font = ImageFont.truetype("arial.ttf", int(height * 0.025))
                except IOError:
                    brand_font = ImageFont.load_default()
                    
            bbox_b = draw.textbbox((0, 0), brand_text, font=brand_font)
            brand_w = bbox_b[2] - bbox_b[0]
            
            # Position: Top right with 30px padding
            brand_x = width - brand_w - 30
            brand_y = 40
            
            # Draw semi-transparent brand text
            draw.text((brand_x+2, brand_y+2), brand_text, font=brand_font, fill=(0,0,0,150))
            draw.text((brand_x, brand_y), brand_text, font=brand_font, fill=(255,255,255,180))
            
            # 3. AI Generated Headline (Bottom Center)
            if watermark_text:
                try:
                    headline_font = ImageFont.truetype("assets/fonts/bold.ttf", int(height * 0.05))
                except IOError:
                    try:
                        headline_font = ImageFont.truetype("arialbd.ttf", int(height * 0.05))
                    except IOError:
                        headline_font = ImageFont.load_default()
                        
                # Split headline into multiple lines if it's too long
                words = watermark_text.split()
                lines = []
                current_line = []
                
                for word in words:
                    current_line.append(word)
                    test_line = " ".join(current_line)
                    bbox_t = draw.textbbox((0, 0), test_line, font=headline_font)
                    if (bbox_t[2] - bbox_t[0]) > (width * 0.85): # Max width 85%
                        current_line.pop()
                        lines.append(" ".join(current_line))
                        current_line = [word]
                if current_line:
                    lines.append(" ".join(current_line))
                    
                line_heights = [draw.textbbox((0, 0), line, font=headline_font)[3] - draw.textbbox((0, 0), line, font=headline_font)[1] for line in lines]
                total_text_height = sum(line_heights) + (len(lines) - 1) * 10
                
                # Draw dark background box for readability
                box_padding = 40
                box_y0 = height - total_text_height - (box_padding * 2) - 50 # 50px from bottom
                box_y1 = height - 50
                
                draw.rectangle([(0, box_y0), (width, box_y1)], fill=(0, 0, 0, 180)) # Semi-transparent black bar across the bottom
                
                # Draw the text lines centered
                current_y = box_y0 + box_padding
                for i, line in enumerate(lines):
                    bbox_l = draw.textbbox((0, 0), line, font=headline_font)
                    line_w = bbox_l[2] - bbox_l[0]
                    line_x = (width - line_w) // 2
                    
                    # Yellow color for headline to stand out
                    draw.text((line_x+3, current_y+3), line, font=headline_font, fill=(0,0,0,255)) # Strong shadow
                    draw.text((line_x, current_y), line, font=headline_font, fill=(255, 215, 0, 255)) # Gold/Yellow text
                    current_y += line_heights[i] + 10
                
            # Combine image and overlay
            watermarked = Image.alpha_composite(img, overlay)
            watermarked = watermarked.convert("RGB") # Convert back to RGB for saving as JPEG
            
            out_dir = os.path.dirname(output_path)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            watermarked.save(output_path, "JPEG", quality=95)
            logging.info(f"Successfully processed image and saved to {output_path}")
            return True
            
    except Exception as e:
        logging.error(f"Failed to process image: {e}")
        return False
