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
    def __init__(self, 
                 ai_config=None, 
                 wp_config=None, 
                 fb_config=None, 
                 gs_config=None, 
                 tg_config=None,
                 config=None,
                 num_threads=5, 
                 limit=None, 
                 language="uk", 
                 debug=False, 
                 disabled_steps=None, 
                 progress_callback=None):
        
        # For backwards compatibility, if a single config object is passed
        if config and not any([ai_config, wp_config, fb_config, gs_config, tg_config]):
            ai_config = {
                "api_key": config.get("ninerouter_api_key"),
                "text_model": config.get("ninerouter_text_model"),
                "image_model": config.get("ninerouter_image_model"),
                "base_url": config.get("ninerouter_base_url", "http://localhost:20128/v1")
            }
            wp_config = {
                "url": config.get("wordpress_url"),
                "username": config.get("wordpress_username"),
                "password": config.get("wordpress_password")
            }
            fb_config = {
                "page_id": config.get("facebook_page_id"),
                "access_token": config.get("facebook_page_access_token"),
                "graph_version": config.get("facebook_graph_version", "v23.0")
            }
            gs_config = {
                "credentials_json": config.get("google_creds_path"),
                "sheet_id": config.get("google_sheets_id")
            }
            tg_config = {
                "bot_token": config.get("telegram_bot_token"),
                "chat_id": config.get("telegram_chat_id")
            }
            self.image_mode = config.get("image_mode", "Direct").lower()
        else:
            self.image_mode = "direct"

        self.ai_config = ai_config
        self.wp_config = wp_config
        self.fb_config = fb_config
        self.gs_config = gs_config
        self.tg_config = tg_config
        
        self.num_threads = num_threads
        self.limit = limit
        self.language = language
        self.debug = debug
        self.disabled_steps = {
            step.strip()
            for step in (disabled_steps or [])
            if isinstance(step, str) and step.strip()
        }
        self.progress_callback = progress_callback
        
        # Initialize providers
        self.ai = NineRouterAI(
            api_key=ai_config.get("api_key"),
            text_model=ai_config.get("text_model"),
            image_model=ai_config.get("image_model"),
            base_url=ai_config.get("base_url", "http://localhost:20128/v1")
        ) if ai_config else None

        self.sheets = GoogleSheetsProvider(
            credentials_json=gs_config.get("credentials_json"),
            sheet_id=gs_config.get("sheet_id")
        ) if gs_config else None

        self.wp = WordPressPublisher(
            url=wp_config.get("url"),
            username=wp_config.get("username"),
            app_password=wp_config.get("password")
        ) if wp_config else None

        self.storage = StorageProvider()
        
        self.fb = FacebookPagePublisher(
            page_id=fb_config.get("page_id"),
            access_token=fb_config.get("access_token"),
            graph_version=fb_config.get("graph_version", "v23.0")
        ) if fb_config else None

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

    def caption_cta(self, language=None):
        lang = (language or self.language or "").strip().lower()
        if lang in {"uk", "ukrainian", "ukraina"}:
            return "Читайте продовження за посиланням у коментарях нижче!"
        if lang in {"vi", "vietnamese"}:
            return "Đọc tiếp ở phần bình luận bên dưới!"
        return "Click the link in the comments below to read the full story!"

    def create_teaser_caption(self, content, language=None):
        words = content.split()
        start = 0
        if len(words) > 650:
            start = max(0, min(len(words) - 450, int(len(words) * 0.45)))
        excerpt = " ".join(words[start:start + 450])
        return f"{excerpt}...\n\n{self.caption_cta(language)}"

    def _emit_progress(self, step_index, step_name, step_progress, detail=""):
        if self.progress_callback:
            self.progress_callback(
                step_index=step_index,
                step_name=step_name,
                step_progress=step_progress,
                detail=detail,
            )

    def _emit_step_ticks(self, step_index, step_name, detail="working"):
        for p in (0, 20, 40, 60, 80, 100):
            self._emit_progress(step_index, step_name, p, detail)

    def _publish_article_payload(self, article_data, task_id, starting_step_index=3, auto_caption=True, status_note=None, notification_prefix_lines=None):
        status = "Success"
        error_msg = ""
        wp_url = ""
        fb_post_id = ""
        fb_post_error = ""
        fb_comment_error = ""
        fb_comment_state = "skipped"

        title = (article_data.get("title") or "").strip()
        content = (article_data.get("content") or "").strip()
        caption = (article_data.get("caption") or "").strip()
        image_url = (article_data.get("image_url") or "").strip()

        if not title or not content:
            raise ValueError("Article payload must include title and content")

        if auto_caption and len(caption.split()) < 300:
            print(f"{task_id} Info: Caption too short, auto-generating excerpt from content...")
            caption = self.create_teaser_caption(content)

        self._emit_step_ticks(starting_step_index, "Publish to WordPress", "working")
        print(f"{task_id} Step {starting_step_index}: Publishing to WordPress...")
        if "wordpress_publish" in self.disabled_steps or not self.wp:
            print(f"{task_id} Info: WordPress publish disabled or not configured")
        else:
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

        self._emit_step_ticks(starting_step_index + 1, "Log to Google Sheets", "working")
        print(f"{task_id} Step {starting_step_index + 1}: Logging to Google Sheets...")
        date_added = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        final_status = status if status == "Success" else f"{status}: {error_msg}"
        if status_note and status == "Success":
            final_status = status_note

        if "google_sheets_log" in self.disabled_steps or not self.sheets:
            print(f"{task_id} Info: Google Sheets log disabled or not configured")
        else:
            self.sheets.append_row([
                title, content, caption, image_url, wp_url, date_added, final_status
            ])
            print(f"{task_id} Sheets Success.")

        self._emit_step_ticks(starting_step_index + 2, "Publish to Facebook", "working")
        print(f"{task_id} Step {starting_step_index + 2}: Publishing to Facebook Page...")
        has_fb_config = bool(self.fb_config and self.fb_config.get("page_id") and self.fb_config.get("access_token"))
        if "facebook_publish" in self.disabled_steps:
            fb_post_error = "Facebook publish disabled"
            fb_comment_state = "skipped"
        elif has_fb_config and self.fb:
            try:
                if image_url:
                    try:
                        fb_post_id = self.fb.publish_photo_caption(caption, image_url)
                    except Exception:
                        fb_post_id = self.fb.publish_text(caption)
                else:
                    fb_post_id = self.fb.publish_text(caption)

                comment_msg = "скажи «так», якщо хочеш продовжити читання історії 👇"
                if wp_url:
                    comment_msg = f"Read full details at the following link: {wp_url}"

                if "facebook_comment" in self.disabled_steps:
                    fb_comment_state = "skipped"
                else:
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
            fb_post_error = "Missing Facebook config" if not has_fb_config else "Facebook provider not initialized"
            fb_comment_state = "skipped"

        print(f"{task_id} Step {starting_step_index + 3}: Telegram Notification...")
        if "telegram_notify" not in self.disabled_steps and self.tg_config:
            try:
                step_lines = list(notification_prefix_lines or [])
                step_lines.append("✅ WordPress" if wp_url else f"❌ WordPress: {error_msg[:80] or 'Failed to publish'}")
                step_lines.append("✅ Google Sheets" if "google_sheets_log" not in self.disabled_steps and self.sheets else "⚪ Google Sheets disabled/missing")
                step_lines.append("✅ Facebook post" if fb_post_id else f"❌ Facebook post: {fb_post_error[:80] or 'Failed'}")

                if fb_comment_state == "success":
                    step_lines.append("✅ FB comment wp_url")
                elif fb_comment_state == "error":
                    step_lines.append(f"❌ FB comment: {fb_comment_error[:80]}")
                elif "facebook_comment" in self.disabled_steps:
                    step_lines.append("⚪ FB comment disabled")
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
                    self.tg_config.get("bot_token"),
                    self.tg_config.get("chat_id"),
                    msg
                )
            except Exception:
                pass
        else:
            print(f"{task_id} Info: Telegram notify disabled or missing config")

        return {"status": "success", "title": title, "url": wp_url}

    def process_article_data(self, article_data):
        task_id = f"[{(article_data.get('source_url') or article_data.get('title') or 'crawl')[:15]}...]"
        try:
            if self.debug:
                df = self.save_debug_file(article_data, prefix="crawl")
                if df:
                    print(f"{task_id} Debug: Crawled article response saved to {df}")
            return self._publish_article_payload(article_data, task_id, starting_step_index=3, auto_caption=True)
        except Exception as e:
            print(f"\n{task_id} ❌ CRITICAL ERROR: {e}")
            date_added = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                self.sheets.append_row([
                    article_data.get("source_url", "crawl")[:100], "ERROR", "", "", "", date_added, f"Critical Error: {str(e)}"
                ])
            except Exception:
                pass
            try:
                if self.tg_config:
                    send_telegram_msg(
                        self.tg_config.get("bot_token"),
                        self.tg_config.get("chat_id"),
                        f"❌ <b>Story Failed</b>\n\nPrompt: {(article_data.get('source_url') or 'crawl')[:120]}\nError: {str(e)[:300]}"
                    )
            except Exception:
                pass
            return {"status": "error", "error": str(e)}

    def process_prompt(self, prompt):
        task_id = f"[{prompt[:15]}...]"
        try:
            self._emit_step_ticks(1, "Generate story text", "working")
            if "ai_text_generation" in self.disabled_steps:
                raise ValueError("Step disabled: ai_text_generation")

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

            print(f"{task_id} AI Success: Title='{title[:30]}...' (Length: {len(content)} chars)")

            self._emit_step_ticks(2, "Generate image", "working")
            image_url = ""
            image_error = ""
            if "ai_image_generation" in self.disabled_steps:
                image_error = "Image generation disabled"
                print(f"{task_id} Info: Image generation disabled")
            elif image_prompt and str(image_prompt).strip():
                print(f"{task_id} Step 2: Generating image via AI...")
                try:
                    image_url = self.ai.generate_image(image_prompt)
                    if self.debug:
                        self.save_debug_file({
                            "status": "success",
                            "image_prompt": image_prompt,
                            "image_url": image_url,
                        }, prefix="image")
                    print(f"{task_id} Image Success: {image_url[:50]}...")
                except Exception as e:
                    image_error = str(e)
                    if self.debug:
                        self.save_debug_file({
                            "status": "error",
                            "image_prompt": image_prompt,
                            "error": image_error,
                        }, prefix="image_fail")
                    print(f"{task_id} Warning: Image generation failed: {image_error[:100]}")
            else:
                image_error = "Missing image_prompt"
                print(f"{task_id} Warning: No image_prompt from AI")

            article_data = {
                "title": title,
                "content": content,
                "caption": caption,
                "image_url": image_url,
            }
            status_note = f"Success (No image: {image_error})" if image_error else None
            notification_prefix_lines = [
                "✅ AI text",
                "✅ AI image" if not image_error else f"❌ AI image: {image_error[:80]}",
            ]
            return self._publish_article_payload(
                article_data,
                task_id,
                starting_step_index=3,
                auto_caption=True,
                status_note=status_note,
                notification_prefix_lines=notification_prefix_lines,
            )

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
                if self.tg_config:
                    send_telegram_msg(
                        self.tg_config.get("bot_token"),
                        self.tg_config.get("chat_id"),
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
