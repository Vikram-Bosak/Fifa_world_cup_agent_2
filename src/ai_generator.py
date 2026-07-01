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

def analyze_and_generate_content(title, description, context=""):
    """
    Analyzes the content and generates all required text formats:
    - image_headline: Viral Style, short, catchy (max 7 words). No emojis.
    - image_subheadline: Catchy subheadline with 1-2 relevant emojis to replace the original text.
    - facebook_post: SEO-optimized full post description with hashtags and emojis.
    - style: Selected visual style.
    - confidence: Confidence score for the style.
    """
    import json
    
    client = get_ai_client()
    if not client:
        logging.warning("No NVIDIA_API_KEY. Falling back to default text.")
        return {
            "image_headline": title[:50],
            "image_subheadline": description[:100],
            "facebook_post": f"⚽ FIFA World Cup Update 🏆\n\n{title}\n\n{description}\n\n#FIFAWorldCup #Soccer",
            "style": "News Style",
            "confidence": "50"
        }
        
    prompt = (
        "You are an expert American sports copywriter and Social Media Manager targeting a US audience. "
        "Analyze the following content carefully. Do NOT use clickbait or false facts. Retain the core meaning.\n\n"
        "CRITICAL RULES FOR TEXT LENGTH:\n"
        "- image_headline: MUST be MAX 6-7 words. Short, punchy, viral. NO EMOJIS. Example: \"SPAIN WINS WORLD CUP\"\n"
        "- image_subheadline: MUST be MAX 15 words. One catchy sentence with 1-2 emojis. Example: \"Historic victory for La Roja! ⚽🏆\"\n"
        "- facebook_post: Full post with hashtags (this can be longer).\n\n"
        "Generate a structured JSON response with exactly these 5 keys:\n"
        "1. \"image_headline\": SHORT viral headline (MAX 6-7 words, NO EMOJIS).\n"
        "2. \"image_subheadline\": SHORT catchy line (MAX 15 words, 1-2 emojis).\n"
        "3. \"facebook_post\": A highly engaging, SEO-optimized Facebook post caption in strict American English (e.g. 'Soccer'). Include a hook, summary, and specific FIFA World Cup hashtags like #FIFAWorldCup #Football #Soccer.\n"
        "4. \"style\": Select ONE visual style that best fits from: Story Style, Meme Style, Cinematic Style, Documentary Style, News Style, Motivational Style, Funny Style, Mixed Style, Other.\n"
        "5. \"confidence\": A score from 0 to 100 on how sure you are about the style classification.\n\n"
        "OUTPUT FORMAT MUST BE STRICTLY VALID JSON. DO NOT INCLUDE ANY MARKDOWN formatting like ```json ... ```. Just raw JSON.\n"
        "CRITICAL: Escape all newlines as \\n and double quotes as \\\" inside your JSON strings so it does not break parsing.\n\n"
        f"TITLE: {title}\n"
        f"DESCRIPTION: {description}\n"
        f"CONTEXT: {context}"
    )
    
    try:
        completion = client.chat.completions.create(
            model="nvidia/nemotron-3-ultra-550b-a55b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            top_p=0.95,
            max_tokens=2048,
            extra_body={"chat_template_kwargs":{"enable_thinking":True},"reasoning_budget":2048},
            stream=False
        )
        
        final_text = completion.choices[0].message.content.strip()
        # Remove any markdown code block artifacts
        if final_text.startswith("```json"):
            final_text = final_text[7:]
        if final_text.startswith("```"):
            final_text = final_text[3:]
        if final_text.endswith("```"):
            final_text = final_text[:-3]
            
        data = json.loads(final_text.strip(), strict=False)
        return {
            "image_headline": data.get("image_headline", title[:50]),
            "image_subheadline": data.get("image_subheadline", description[:100]),
            "facebook_post": data.get("facebook_post", f"{title}\n\n{description}"),
            "style": data.get("style", "News Style"),
            "confidence": str(data.get("confidence", "80"))
        }
    except Exception as e:
        logging.error(f"AI content generation failed or JSON parse error: {e}")
        return {
            "image_headline": title[:50],
            "image_subheadline": description[:100],
            "facebook_post": f"⚽ Update 🏆\n\n{title}\n\n{description}\n\n#FIFAWorldCup",
            "style": "News Style",
            "confidence": "50"
        }
