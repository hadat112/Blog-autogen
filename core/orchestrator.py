import os
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

from providers.ai_9router import NineRouterAI
from providers.google_sheets import GoogleSheetsProvider
from providers.storage import StorageProvider
from publishers.wp_rest import WordPressPublisher
from utils.helpers import send_telegram_msg

class Orchestrator:
    def __init__(self, config, num_threads=5, limit=None):
        self.config = config
        self.num_threads = num_threads
        self.limit = limit
        
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

    def process_prompt(self, prompt):
        """
        Logic for a single task:
        1. AI: generate_story(prompt)
        2. AI: generate_image(image_prompt)
        3. Storage: (Optional) download image if image_mode == 'local'
        4. WP: publish(title, content, image)
        5. Sheets: append_row(...)
        6. Telegram: send_telegram_msg(...)
        """
        status = "Success"
        error_msg = ""
        wp_url = ""
        
        # Use first 20 chars of prompt for identification in logs
        task_id = f"[{prompt[:20]}...]"
        
        try:
            # 1. AI Text Generation
            logging.info(f"{task_id} Generating story and caption via AI...")
            story_data = self.ai.generate_story(prompt)
            title = story_data.get("title")
            content = story_data.get("content")
            caption = story_data.get("caption")
            image_prompt = story_data.get("image_prompt")
            
            # 2. AI Image Generation
            logging.info(f"{task_id} Generating image via AI...")
            image_url = self.ai.generate_image(image_prompt)
            
            # 3. Storage (Optional download)
            image_to_publish = image_url
            temp_path = None
            if self.image_mode == "local":
                try:
                    logging.info(f"{task_id} Downloading image locally...")
                    temp_path = self.storage.download_image(image_url)
                    image_to_publish = temp_path
                except Exception as e:
                    logging.error(f"{task_id} Failed to download image: {e}")
                    pass
            
            # 4. WordPress Publishing
            logging.info(f"{task_id} Publishing to WordPress...")
            try:
                wp_url = self.wp.publish(title, content, image_to_publish)
                logging.info(f"{task_id} ✅ Published: {wp_url}")
            finally:
                if temp_path:
                    self.storage.cleanup(temp_path)
            
            # 5. Sheets Logging
            logging.info(f"{task_id} Logging to Google Sheets...")
            date_added = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.sheets.append_row([
                title, content, caption, image_url, wp_url, date_added, status
            ])
            
            # 6. Telegram Notification
            logging.info(f"{task_id} Sending Telegram notification...")
            msg = f"✅ <b>Story Published!</b>\n\nTitle: {title}\nURL: {wp_url}"
            send_telegram_msg(
                self.config.get("telegram_bot_token"),
                self.config.get("telegram_chat_id"),
                msg
            )
            
            return {"status": "success", "title": title, "url": wp_url}

        except Exception as e:
            status = "Error"
            error_msg = str(e)
            logging.error(f"Error processing prompt '{prompt}': {error_msg}")
            
            # Try to log error to sheets if possible (some fields might be missing)
            try:
                date_added = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.sheets.append_row([
                    prompt, "", "", "", "", date_added, f"Error: {error_msg}"
                ])
            except:
                pass
                
            # Notify via Telegram about the error
            try:
                err_msg = f"❌ <b>Error processing story</b>\n\nPrompt: {prompt}\nError: {error_msg}"
                send_telegram_msg(
                    self.config.get("telegram_bot_token"),
                    self.config.get("telegram_chat_id"),
                    err_msg
                )
            except:
                pass
                
            return {"status": "error", "prompt": prompt, "error": error_msg}

    def run(self, prompts_file):
        if not os.path.exists(prompts_file):
            logging.error(f"Prompts file not found: {prompts_file}")
            return []
            
        with open(prompts_file, "r") as f:
            prompts = [line.strip() for line in f if line.strip()]
            
        if self.limit:
            prompts = prompts[:self.limit]
            
        results = []
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            try:
                # Using tqdm for progress bar
                # Use executor.submit to have more control over futures if needed
                # but map is okay if we wrap the whole thing
                results = list(tqdm(executor.map(self.process_prompt, prompts), total=len(prompts), desc="Processing stories"))
            except KeyboardInterrupt:
                print("\nStopping orchestrator... Cancelling pending tasks.")
                executor.shutdown(wait=False, cancel_futures=True)
                raise # Re-raise to be caught in main.py
            
        return results
