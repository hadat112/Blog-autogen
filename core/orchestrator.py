import os
import logging
import json
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

from adapters.ai.ninerouter import NineRouterAI
from adapters.loggers.google_sheets import GoogleSheetsProvider
from adapters.storage.local import StorageProvider
from adapters.publishers.wordpress import WordPressPublisher
from adapters.publishers.facebook_page import FacebookPagePublisher
from adapters.notifiers.telegram import send_telegram_msg
from core.pipeline import (
    ArticlePayload,
    PipelineCore,
    PipelinePorts,
    PipelineState,
    create_step,
)
import core.pipeline.steps  # noqa: F401 - import registers built-in pipeline steps


PUBLICATION_STEP_IDS = [
    "prepare_caption",
    "wordpress_publish",
    "google_sheets_log",
    "facebook_publish",
    "telegram_notify",
]

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
                 language="Ukrainian",
                 debug=False,
                 disabled_steps=None,
                 progress_callback=None):

        # For backwards compatibility, if a single config object is passed
        if config and not any([ai_config, wp_config, fb_config, gs_config, tg_config]):
            ai_config = {
                "api_key": config.get("ninerouter_api_key"),
                "text_model": config.get("ninerouter_text_model"),
                "image_model": config.get("ninerouter_image_model"),
                "base_url": config.get("ninerouter_base_url", "http://localhost:20128/v1"),
                "translation_mode": config.get("translation_mode", "sequential"),
                "translation_max_concurrency": config.get("translation_max_concurrency", 2),
                "ai_request_timeout": config.get("ai_request_timeout", 300),
                "translation_chunk_size": config.get("translation_chunk_size", 6000),
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
            base_url=ai_config.get("base_url", "http://localhost:20128/v1"),
            translation_mode=ai_config.get("translation_mode", "sequential"),
            translation_max_concurrency=ai_config.get("translation_max_concurrency", 2),
            ai_request_timeout=ai_config.get("ai_request_timeout", 300),
            translation_chunk_size=ai_config.get("translation_chunk_size", 6000),
        ) if ai_config else None

        self.sheets = GoogleSheetsProvider(
            credentials_json=gs_config.get("credentials_path") or gs_config.get("credentials_json") or "credentials.json",
            sheet_id=gs_config.get("spreadsheet_id") or gs_config.get("sheet_id")
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

    def prompt_language_hint(self):
        return self.language

    def apply_language_to_prompt(self, prompt):
        return prompt.replace("{language}", self.prompt_language_hint()) if "{language}" in prompt else prompt

    def apply_language_to_prompts(self, prompts):
        return [self.apply_language_to_prompt(p) for p in prompts] if prompts else prompts

    def enforce_story_language(self, prompt):
        return (
            "MANDATORY OUTPUT LANGUAGE\n"
            f"Target language: {self.language}\n"
            f"Write every reader-facing word in title, content, and caption in {self.language} only.\n"
            "Do not switch to English or any other language. Do not translate, normalize, "
            "reinterpret, or replace the target language value.\n"
            "The caption CTA must also be written in the same target language.\n"
            "Before returning JSON, verify that no ordinary sentence in title, content, or "
            "caption is written in another language.\n\n"
            f"{prompt}"
        )

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
        return ""

    def create_teaser_caption(self, content, language=None):
        words = content.split()
        start = 0
        if len(words) > 650:
            start = max(0, min(len(words) - 450, int(len(words) * 0.45)))
        excerpt = " ".join(words[start:start + 450])
        cta = self.caption_cta(language)
        return f"{excerpt}...\n\n{cta}" if cta else f"{excerpt}..."

    def build_publication_core(self, starting_step_index):
        step_indexes = {
            "prepare_caption": starting_step_index - 1,
            "wordpress_publish": starting_step_index,
            "google_sheets_log": starting_step_index + 1,
            "facebook_publish": starting_step_index + 2,
            "telegram_notify": starting_step_index + 3,
        }
        return PipelineCore([
            create_step(step_id, step_index=step_indexes[step_id])
            for step_id in PUBLICATION_STEP_IDS
        ])

    def build_ports(self):
        return PipelinePorts(
            wp=self.wp,
            wp_config=self.wp_config,
            sheets=self.sheets,
            fb=self.fb,
            tg_config=self.tg_config,
            telegram_sender=send_telegram_msg,
            storage=self.storage,
            image_mode=self.image_mode,
        )

    def _emit_progress(self, step_index, step_name, step_progress, detail="", task_id=None):
        if self.progress_callback:
            # We add task_id to the callback call
            try:
                self.progress_callback(
                    step_index=step_index,
                    step_name=step_name,
                    step_progress=step_progress,
                    detail=detail,
                    task_id=task_id
                )
            except TypeError:
                # Fallback for old callback signature if needed
                self.progress_callback(
                    step_index=step_index,
                    step_name=step_name,
                    step_progress=step_progress,
                    detail=detail
                )

    def _emit_step_ticks(self, step_index, step_name, detail="working", task_id=None):
        for p in (0, 20, 40, 60, 80, 100):
            self._emit_progress(step_index, step_name, p, detail, task_id=task_id)

    def _emit_log(self, message, step_index=0, step_name="Log", progress=0, task_id=None):
        print(message)
        self._emit_progress(step_index, step_name, progress, message, task_id=task_id)

    def _publish_article_payload(self, article_data, log_task_id, starting_step_index=3, auto_caption=True, status_note=None, notification_prefix_lines=None, task_id=None):
        article = ArticlePayload.from_dict(article_data)
        state = PipelineState(
            article=article,
            disabled_steps=set(self.disabled_steps),
            language_name=self.language,
            caption_cta=self.caption_cta(),
            log_task_id=log_task_id,
            task_id=task_id,
            auto_caption=auto_caption,
            status_note=status_note,
            notification_prefix_lines=list(notification_prefix_lines or []),
        )

        def emit(step_index, step_name, progress, detail, emit_task_id=None):
            if detail == "working":
                self._emit_progress(step_index, step_name, progress, detail, task_id=emit_task_id)
            else:
                self._emit_log(detail, step_index, step_name, progress, task_id=emit_task_id)

        return self.build_publication_core(starting_step_index).run(
            state=state,
            ports=self.build_ports(),
            emit=emit,
        )

    def process_article_data(self, article_data, task_id=None):
        log_task_id = f"[{(article_data.get('source_url') or article_data.get('title') or 'crawl')[:15]}...]"
        try:
            if self.debug:
                df = self.save_debug_file(article_data, prefix="crawl")
                if df:
                    print(f"{log_task_id} Debug: Crawled article response saved to {df}")
            return self._publish_article_payload(article_data, log_task_id, starting_step_index=3, auto_caption=True, task_id=task_id)
        except Exception as e:
            print(f"\n{log_task_id} ❌ CRITICAL ERROR: {e}")
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

    def process_crawl(self, url, task_id=None):
        log_task_id = f"[{url[:15]}...]"
        try:
            self._emit_step_ticks(1, "Extract article from URL", "working", task_id=task_id)
            self._emit_log(f"{log_task_id} Step 1: Extracting article from {url}...", 1, "Extract article from URL", 0, task_id=task_id)

            from core.article_crawler import extract_article_from_url

            def crawl_log(message):
                self._emit_log(f"{log_task_id} {message}", 2, "AI Translate", 0, task_id=task_id)

            article_data = extract_article_from_url(
                url,
                self.ai,
                language=self.language,
                log_callback=crawl_log,
                translate=bool((self.language or "").strip()),
            )

            self._emit_log(f"{log_task_id} Extraction Success: Title='{article_data.get('title', '')[:30]}...'", 1, "Extract article from URL", 100, task_id=task_id)

            # Step 2 in crawl is usually image generation or skip
            self._emit_progress(2, "AI Translate", 100, f"{log_task_id} AI Translate Success", task_id=task_id)

            return self._publish_article_payload(
                article_data,
                log_task_id,
                starting_step_index=3,
                auto_caption=True,
                task_id=task_id
            )
        except Exception as e:
            self._emit_log(f"{log_task_id} CRAWL ERROR: {e}", 0, "Error", 0, task_id=task_id)
            self._emit_progress(0, "Error", 0, str(e), task_id=task_id)
            raise e

    def process_prompt(self, prompt, task_id=None):
        log_task_id = f"[{prompt[:15]}...]"
        try:
            self._emit_step_ticks(1, "Generate story text", "working", task_id=task_id)
            if "ai_text_generation" in self.disabled_steps:
                raise ValueError("Step disabled: ai_text_generation")

            print(f"\n{log_task_id} Step 1: Generating story via AI...")
            try:
                story_data = self.ai.generate_story(
                    self.enforce_story_language(prompt)
                )
                df = self.save_debug_file(story_data)
                if df:
                    print(f"{log_task_id} Debug: AI response saved to {df}")
            except Exception as e:
                err_str = str(e)
                if "Raw content:" in err_str:
                    raw_part = err_str.split("Raw content:")[1].strip()
                    df = self.save_debug_file(raw_part, prefix="fail")
                    if df:
                        print(f"{log_task_id} Debug: Failed AI raw content saved to {df}")
                raise e

            title = story_data.get("title", "")
            content = story_data.get("content", "")
            caption = story_data.get("caption", "")
            image_prompt = story_data.get("image_prompt", "")

            print(f"{log_task_id} AI Success: Title='{title[:30]}...' (Length: {len(content)} chars)")

            self._emit_step_ticks(2, "Generate image", "working", task_id=task_id)
            image_url = ""
            image_error = ""
            if "ai_image_generation" in self.disabled_steps:
                image_error = "Image generation disabled"
                print(f"{log_task_id} Info: Image generation disabled")
            elif image_prompt and str(image_prompt).strip():
                print(f"{log_task_id} Step 2: Generating image via AI...")
                try:
                    image_url = self.ai.generate_image(image_prompt)
                    if self.debug:
                        self.save_debug_file({
                            "status": "success",
                            "image_prompt": image_prompt,
                            "image_url": image_url,
                        }, prefix="image")
                    print(f"{log_task_id} Image Success: {image_url[:50]}...")
                except Exception as e:
                    image_error = str(e)
                    if self.debug:
                        self.save_debug_file({
                            "status": "error",
                            "image_prompt": image_prompt,
                            "error": image_error,
                        }, prefix="image_fail")
                    print(f"{log_task_id} Warning: Image generation failed: {image_error[:100]}")
            else:
                image_error = "Missing image_prompt"
                print(f"{log_task_id} Warning: No image_prompt from AI")

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
                log_task_id,
                starting_step_index=3,
                auto_caption=True,
                status_note=status_note,
                notification_prefix_lines=notification_prefix_lines,
                task_id=task_id
            )

        except Exception as e:
            print(f"\n{log_task_id} ❌ CRITICAL ERROR: {e}")
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
            # When running multiple stories, we create a unique task_id for each story thread
            import uuid
            futures = []
            for prompt in prompts:
                task_id = str(uuid.uuid4())
                futures.append(executor.submit(self.process_prompt, prompt, task_id=task_id))

            results = [f.result() for f in tqdm(futures, total=len(futures), desc="Processing stories")]

        return results
