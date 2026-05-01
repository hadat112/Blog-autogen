import os
import logging
import json
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

from providers.ai_9router import NineRouterAI
from providers.google_sheets import GoogleSheetsProvider
from providers.storage import StorageProvider
from publishers.wp_rest import WordPressPublisher
from utils.helpers import send_telegram_msg

class Orchestrator:
    def __init__(self, config, num_threads=5, limit=None, language="vi", debug=False):
        self.config = config
        self.num_threads = num_threads
        self.limit = limit
        self.language = language
        self.debug = debug
        
        # Initialize providers
        self.ai = NineRouterAI(
            api_key=config.get("ninerouter_api_key"),
            text_model=config.get("ninerouter_text_model"),
            image_model=config.get("ninerouter_image_model"),
            base_url=config.get("ninerouter_base_url", "http://localhost:20128/v1")
        )
        self.sheets = GoogleSheetsProvider(
            credentials_json=config.get("google_creds_path"),
            sheet_id=config.get("google_sheets_id")
        )
        self.wp = WordPressPublisher(
            url=config.get("wordpress_url"),
            username=config.get("wordpress_username"),
            app_password=config.get("wordpress_password")
        )
        self.storage = StorageProvider()
        
        self.image_mode = config.get("image_mode", "Direct").lower()
        
        if self.debug:
            os.makedirs("debug", exist_ok=True)

    def save_debug_file(self, content, prefix="story"):
        if not self.debug:
            return
        timestamp = datetime.now().strftime("%m%d_%H%M%S")
        filename = f"debug/{prefix}_{timestamp}.json"
        if isinstance(content, str):
            content = {"raw_content": content}
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            return filename
        except Exception as e:
            print(f"Failed to save debug file: {e}")
            return None

    def create_teaser_caption(self, content):
        """Creates a word-for-word excerpt from the first ~400 words of content."""
        words = content.split()
        excerpt = " ".join(words[:400])
        cta = "Hãy bấm vào link trong comment dưới đây để đọc full truyện!"
        if self.language != "vi":
            cta = "Click the link in the comments below to read the full story!"
            
        return f"{excerpt}...\n\n{cta}"

    def process_prompt(self, prompt):
        status = "Success"
        error_msg = ""
        wp_url = ""
        image_url = ""
        image_error = ""
        
        title = ""
        content = ""
        caption = ""
        
        task_id = f"[{prompt[:15]}...]"
        
        try:
            # 1. AI Text Generation
            print(f"\n{task_id} Step 1: Generating story via AI...")
            try:
                story_data = self.ai.generate_story(prompt)
                df = self.save_debug_file(story_data)
                if df: print(f"{task_id} Debug: AI response saved to {df}")
            except Exception as e:
                err_str = str(e)
                if "Raw content:" in err_str:
                    raw_part = err_str.split("Raw content:")[1].strip()
                    df = self.save_debug_file(raw_part, prefix="fail")
                    if df: print(f"{task_id} Debug: Failed AI raw content saved to {df}")
                raise e

            title = story_data.get("title", "")
            content = story_data.get("content", "")
            caption = story_data.get("caption", "")
            image_prompt = story_data.get("image_prompt", "")
            
            # AUTO-FIX CAPTION if AI failed to provide a long enough excerpt
            # If caption is less than 150 chars or looks like a summary, use code to excerpt
            if len(caption) < 200:
                print(f"{task_id} Info: AI caption too short, auto-generating excerpt from content...")
                caption = self.create_teaser_caption(content)
            
            # Ensure CTA is in caption
            cta_vi = "Hãy bấm vào link trong comment dưới đây để đọc full truyện!"
            if cta_vi not in caption and self.language == "vi":
                caption = caption.rstrip() + f"\n\n{cta_vi}"

            print(f"{task_id} AI Success: Title='{title[:30]}...' (Length: {len(content)} chars)")
            
            # 2. AI Image Generation
            if image_prompt and str(image_prompt).strip():
                print(f"{task_id} Step 2: Generating image via AI...")
                try:
                    image_url = self.ai.generate_image(image_prompt)
                    print(f"{task_id} Image Success: {image_url[:50]}...")
                except Exception as e:
                    image_error = str(e)
                    print(f"{task_id} Warning: Image generation failed: {image_error[:100]}")
            else:
                image_error = "Missing image_prompt"
                print(f"{task_id} Warning: No image_prompt from AI")
            
            # 3. WordPress Publishing
            print(f"{task_id} Step 3: Publishing to WordPress...")
            try:
                image_to_publish = image_url
                temp_path = None
                if self.image_mode == "local" and image_url:
                    try:
                        temp_path = self.storage.download_image(image_url)
                        image_to_publish = temp_path
                    except:
                        image_to_publish = image_url

                wp_url = self.wp.publish(title, content, image_to_publish)
                print(f"{task_id} WP Success: {wp_url}")
                
                if temp_path:
                    self.storage.cleanup(temp_path)
            except Exception as e:
                status = f"Partial Success (WP Error)"
                error_msg = str(e)
                print(f"{task_id} Warning: WordPress publishing failed: {error_msg[:100]}")

            # 4. Sheets Logging
            print(f"{task_id} Step 4: Logging to Google Sheets...")
            date_added = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            final_status = status if status == "Success" else f"{status}: {error_msg}"
            if image_error and status == "Success":
                final_status = f"Success (No image: {image_error})"

            self.sheets.append_row([
                title, content, caption, image_url, wp_url, date_added, final_status
            ])
            print(f"{task_id} Sheets Success.")
            
            # 5. Telegram Notification
            try:
                msg = f"✅ <b>Story Processed!</b>\n\nTitle: {title}\nWP: {wp_url or 'Failed'}"
                if image_error: msg += f"\n⚠️ Image fail: {image_error[:50]}"
                if error_msg: msg += f"\n❌ WP fail: {error_msg[:50]}"
                
                send_telegram_msg(
                    self.config.get("telegram_bot_token"),
                    self.config.get("telegram_chat_id"),
                    msg
                )
            except: pass
            
            return {"status": "success", "title": title, "url": wp_url}

        except Exception as e:
            print(f"\n{task_id} ❌ CRITICAL ERROR: {e}")
            date_added = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                self.sheets.append_row([
                    prompt[:100], "ERROR", "", "", "", date_added, f"Critical Error: {str(e)}"
                ])
            except: pass
            return {"status": "error", "error": str(e)}

    def run(self, prompts_file):
        if not os.path.exists(prompts_file):
            return []
            
        with open(prompts_file, "r") as f:
            raw_prompts = f.read().strip()

        if "## TASK" in raw_prompts and "\n" in raw_prompts:
            prompts = [raw_prompts]
        else:
            prompts = [line.strip() for line in raw_prompts.splitlines() if line.strip()]

        prompts = [p.replace("{language}", self.language) for p in prompts]
            
        if self.limit:
            prompts = prompts[:self.limit]
            
        results = []
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            results = list(tqdm(executor.map(self.process_prompt, prompts), total=len(prompts), desc="Processing stories"))
            
        return results
