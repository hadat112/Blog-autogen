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
from publishers.facebook_page import FacebookPagePublisher
from utils.helpers import send_telegram_msg

class Orchestrator:
    def __init__(self, config, num_threads=5, limit=None, language="uk", debug=False):
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
        self.fb = FacebookPagePublisher(
            page_id=config.get("facebook_page_id"),
            access_token=config.get("facebook_page_access_token"),
            graph_version=config.get("facebook_graph_version", "v23.0")
        )

        self.image_mode = config.get("image_mode", "Direct").lower()

        if self.debug:
            os.makedirs("debug", exist_ok=True)

    def prompt_language_name(self):
        lang = (self.language or "").strip().lower()
        if lang == "uk":
            return "Ukrainian"
        if lang == "en":
            return "English"
        if lang == "vi":
            return "Vietnamese"
        return self.language

    def prompt_language_hint(self):
        lang_name = self.prompt_language_name()
        return f"{lang_name} (code: {self.language})" if self.language else lang_name

    def apply_language_to_prompt(self, prompt):
        return prompt.replace("{language}", self.prompt_language_hint()) if "{language}" in prompt else prompt

    def apply_language_to_prompts(self, prompts):
        return [self.apply_language_to_prompt(p) for p in prompts] if prompts else prompts

    def load_prompts(self, prompts_file):
        with open(prompts_file, "r") as f:
            raw_prompts = f.read().strip()

        if "## TASK" in raw_prompts and "\n" in raw_prompts:
            prompts = [raw_prompts]
        else:
            prompts = [line.strip() for line in raw_prompts.splitlines() if line.strip()]

        return self.apply_language_to_prompts(prompts) if prompts else []

    def _read_prompts(self, prompts_file):
        return self.load_prompts(prompts_file)

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
        cta = "Click the link in the comments below to read the full story!"
            
        return f"{excerpt}...\n\n{cta}"

    def process_prompt(self, prompt):
        status = "Success"
        error_msg = ""
        wp_url = ""
        image_url = ""
        image_error = ""
        fb_post_id = ""
        fb_post_error = ""
        fb_comment_error = ""
        fb_comment_state = "skipped"

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
                if df:
                    print(f"{task_id} Debug: AI response saved to {df}")
            except Exception as e:
                err_str = str(e)
                if "Raw content:" in err_str:
                    raw_part = err_str.split("Raw content:")[1].strip()
                    df = self.save_debug_file(raw_part, prefix="fail")
                    if df:
                        print(f"{task_id} Debug: Failed AI raw content saved to {df}")
                raise e

            title = story_data.get("title", "")
            content = story_data.get("content", "")
            caption = story_data.get("caption", "")
            image_prompt = story_data.get("image_prompt", "")

            if len(caption) < 200:
                print(f"{task_id} Info: AI caption too short, auto-generating excerpt from content...")
                caption = self.create_teaser_caption(content)

            cta_en = "Click the link in the comments below to read the full story!"
            if cta_en not in caption and self.language == "en":
                caption = caption.rstrip() + f"\n\n{cta_en}"

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
                    except Exception:
                        image_to_publish = image_url

                wp_url = self.wp.publish(title, content, image_to_publish)
                print(f"{task_id} WP Success: {wp_url}")

                if temp_path:
                    self.storage.cleanup(temp_path)
            except Exception as e:
                status = "Partial Success (WP Error)"
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

            # 5. Facebook Page Publishing
            print(f"{task_id} Step 5: Publishing to Facebook Page...")
            has_fb_config = bool(self.config.get("facebook_page_id") and self.config.get("facebook_page_access_token"))
            if has_fb_config:
                try:
                    if image_url:
                        try:
                            fb_post_id = self.fb.publish_photo_caption(caption, image_url)
                        except Exception:
                            fb_post_id = self.fb.publish_text(caption)
                    else:
                        fb_post_id = self.fb.publish_text(caption)

                    comment_msg = "Read full details at the following link"
                    if wp_url:
                        comment_msg = f"Read full details at the following link: {wp_url}"

                    try:
                        self.fb.comment_on_post(fb_post_id, comment_msg)
                        fb_comment_state = "success"
                    except Exception as e:
                        fb_comment_state = "error"
                        fb_comment_error = str(e)
                except Exception as e:
                    fb_post_error = str(e)
                    fb_comment_state = "skipped"
            else:
                fb_post_error = "Missing Facebook config"
                fb_comment_state = "skipped"

            # 6. Telegram Notification
            print(f"{task_id} Step 6: Telegram Notification...")
            try:
                step_lines = []
                step_lines.append("✅ AI text")
                step_lines.append("✅ AI image" if not image_error else f"❌ AI image: {image_error[:80]}")
                step_lines.append("✅ WordPress" if wp_url else f"❌ WordPress: {error_msg[:80] or 'Failed to publish'}")
                step_lines.append("✅ Google Sheets")
                step_lines.append("✅ Facebook post" if fb_post_id else f"❌ Facebook post: {fb_post_error[:80] or 'Failed'}")

                if fb_comment_state == "success":
                    step_lines.append("✅ FB comment wp_url")
                elif fb_comment_state == "error":
                    step_lines.append(f"❌ FB comment: {fb_comment_error[:80]}")
                else:
                    step_lines.append("⚪ FB comment skipped (no wp_url)")

                msg = (
                    "✅ <b>Story Processed!</b>\n\n"
                    f"Title: {title}\n"
                    + "\n".join(step_lines)
                    + f"\n\nWP: {wp_url or 'N/A'}"
                    + f"\nFB Post ID: {fb_post_id or 'N/A'}"
                )

                send_telegram_msg(
                    self.config.get("telegram_bot_token"),
                    self.config.get("telegram_chat_id"),
                    msg
                )
            except Exception:
                pass

            return {"status": "success", "title": title, "url": wp_url}

        except Exception as e:
            print(f"\n{task_id} ❌ CRITICAL ERROR: {e}")
            date_added = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                self.sheets.append_row([
                    prompt[:100], "ERROR", "", "", "", date_added, f"Critical Error: {str(e)}"
                ])
            except Exception:
                pass

            try:
                send_telegram_msg(
                    self.config.get("telegram_bot_token"),
                    self.config.get("telegram_chat_id"),
                    f"❌ <b>Story Failed</b>\n\nPrompt: {prompt[:120]}\nError: {str(e)[:300]}"
                )
            except Exception:
                pass

            return {"status": "error", "error": str(e)}

    def run(self, prompts_file):
        if not os.path.exists(prompts_file):
            return []
            
        prompts = self._read_prompts(prompts_file)

        if self.limit:
            prompts = prompts[:self.limit]
            
        results = []
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            results = list(tqdm(executor.map(self.process_prompt, prompts), total=len(prompts), desc="Processing stories"))
            
        return results
