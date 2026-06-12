import os
import logging
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_ai_client():
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        return None
        
    try:
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key,
            timeout=30.0 # 30 second timeout
        )
        return client
    except Exception as e:
        logging.error(f"Failed to initialize OpenAI client: {e}")
        return None

def generate_headline(title, description=""):
    """
    Generates a short, catchy, American English headline to overlay on the image.
    Falls back to the original title if AI fails.
    """
    client = get_ai_client()
    if not client:
        logging.warning("No NVIDIA_API_KEY. Falling back to original title.")
        return title[:50]
        
    prompt = (
        "You are an expert American sports copywriter targeting a US audience. "
        "Analyze the following post title and description, and generate a very short, punchy, "
        "and catchy headline (MAXIMUM 5 to 7 WORDS) to be placed as text ON TOP of an image.\n\n"
        "RULES:\n"
        "1. MUST use strict American English spelling and terminology (e.g., 'Soccer' instead of 'Football', 'Favorite', 'Color', etc).\n"
        "2. Do NOT use emojis.\n"
        "3. Do NOT put quotes around the output.\n"
        "4. Return ONLY the final text for the headline.\n\n"
        f"TITLE: {title}\n"
        f"DESCRIPTION: {description}"
    )
    
    try:
        completion = client.chat.completions.create(
            model="nvidia/nemotron-3-ultra-550b-a55b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            top_p=0.95,
            max_tokens=1024,
            extra_body={"chat_template_kwargs":{"enable_thinking":True},"reasoning_budget":1024},
            stream=True
        )
        
        final_text = ""
        for chunk in completion:
            if not chunk.choices:
                continue
            if chunk.choices[0].delta.content is not None:
                final_text += chunk.choices[0].delta.content
                
        headline = final_text.strip().strip('"\'')
        if headline:
            return headline
        return title[:50]
    except Exception as e:
        logging.error(f"AI headline generation failed: {e}")
        return title[:50]

def generate_facebook_post(title, description=""):
    """
    Generates an SEO-optimized Facebook post caption in American English.
    Falls back to original title/description if AI fails.
    """
    client = get_ai_client()
    if not client:
        logging.warning("No NVIDIA_API_KEY. Falling back to default Facebook text.")
        return f"⚽ FIFA World Cup Update 🏆\n\n{title}\n\n{description}\n\n#FIFAWorldCup #Soccer #USMNT"
        
    prompt = (
        "You are an expert Social Media Manager targeting a United States audience for a FIFA World Cup Facebook page. "
        "Write a highly engaging, SEO-optimized Facebook post caption based on the following Title and Description.\n\n"
        "RULES:\n"
        "1. MUST use STRICT American English (e.g. 'Soccer', 'Color', 'Organize', 'Favorite'). NEVER use British/Indian variants.\n"
        "2. Include an engaging hook, a brief summary or hype, and a clear Call-to-Action (CTA) for the US audience.\n"
        "3. Include relevant US-centric hashtags (e.g. #Soccer, #USMNT, #FIFAWorldCup26, #TeamUSA).\n"
        "4. Do NOT output anything other than the final Facebook post text.\n\n"
        f"TITLE: {title}\n"
        f"DESCRIPTION: {description}"
    )
    
    try:
        completion = client.chat.completions.create(
            model="nvidia/nemotron-3-ultra-550b-a55b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            top_p=0.95,
            max_tokens=2048,
            extra_body={"chat_template_kwargs":{"enable_thinking":True},"reasoning_budget":2048},
            stream=True
        )
        
        final_text = ""
        for chunk in completion:
            if not chunk.choices:
                continue
            if chunk.choices[0].delta.content is not None:
                final_text += chunk.choices[0].delta.content
                
        post_text = final_text.strip()
        if post_text:
            return post_text
            
        return f"⚽ FIFA World Cup Update 🏆\n\n{title}\n\n{description}\n\n#FIFAWorldCup #Soccer #USMNT"
    except Exception as e:
        logging.error(f"AI Facebook post generation failed: {e}")
        return f"⚽ FIFA World Cup Update 🏆\n\n{title}\n\n{description}\n\n#FIFAWorldCup #Soccer #USMNT"
