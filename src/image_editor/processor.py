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
            
            # If logo exists, paste it at the bottom right
            if logo_path and os.path.exists(logo_path):
                try:
                    with Image.open(logo_path) as logo:
                        logo = logo.convert("RGBA")
                        # Resize logo to 15% of image width
                        logo_width = int(width * 0.15)
                        w_percent = (logo_width / float(logo.size[0]))
                        logo_height = int((float(logo.size[1]) * float(w_percent)))
                        logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
                        
                        # Position: bottom right with 20px padding
                        pos_x = width - logo_width - 20
                        pos_y = height - logo_height - 20
                        overlay.paste(logo, (pos_x, pos_y), logo)
                except Exception as e:
                    logging.warning(f"Could not add logo: {e}")
            
            # Add simple text watermark if no logo
            else:
                try:
                    # Attempt to load a default font
                    font = ImageFont.truetype("arial.ttf", int(height * 0.05))
                except IOError:
                    font = ImageFont.load_default()
                    
                # We use textbbox to get text size
                bbox = draw.textbbox((0, 0), watermark_text, font=font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                
                pos_x = width - text_w - 20
                pos_y = height - text_h - 20
                
                # Draw text with a slight shadow for visibility
                draw.text((pos_x+2, pos_y+2), watermark_text, font=font, fill=(0,0,0,128))
                draw.text((pos_x, pos_y), watermark_text, font=font, fill=(255,255,255,200))
                
            # Combine image and overlay
            watermarked = Image.alpha_composite(img, overlay)
            watermarked = watermarked.convert("RGB") # Convert back to RGB for saving as JPEG
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            watermarked.save(output_path, "JPEG", quality=95)
            logging.info(f"Successfully processed image and saved to {output_path}")
            return True
            
    except Exception as e:
        logging.error(f"Failed to process image: {e}")
        return False
