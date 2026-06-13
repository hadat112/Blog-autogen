import json
import re
import time
from html import unescape
from html.parser import HTMLParser

import requests

from .base import BaseAI


REQUIRED_STORY_KEYS = ("title", "content", "caption", "image_prompt")
REQUIRED_ARTICLE_KEYS = ("title", "content", "caption", "image_url")
CINEMATIC_NATURALISM_STYLE_PROMPT = (
    "Naturalistic high-key daylight lighting, vivid and clean color palette, neutral white balance, "
    "realistic skin tones with zero color tint, sharp clarity, 8k professional photography, "
    "shot on full-frame sensor for authentic color reproduction, no moody color grading, "
    "no teal-orange look, no heavy shadows, no dramatic dark tone."
)
TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
AI_REQUEST_TIMEOUT = 60
AI_MAX_ATTEMPTS = 2
TRANSLATION_TEMPERATURE = 0.2
CHUNKED_ARTICLE_THRESHOLD = 8000
TRANSLATION_CHUNK_SIZE = 1800
TRANSLATION_CONTEXT_PARAGRAPHS = 1
TRANSLATION_PREFIX_RE = re.compile(
    r"^\s*(?:"
    r"(?:sure|certainly|of course)[,!.:\s-]+|"
    r"(?:here(?:'s| is)?\s+(?:the\s+)?(?:translation|translated text)[.:]\s*)|"
    r"(?:(?:translation|translated text|bản dịch)\s*:)\s*"
    r")",
    re.IGNORECASE,
)
def _build_styled_image_prompt(image_prompt: str) -> str:
    base_prompt = (image_prompt or "").strip()
    if base_prompt:
        return f"{base_prompt}\n\n{CINEMATIC_NATURALISM_STYLE_PROMPT}"
    return CINEMATIC_NATURALISM_STYLE_PROMPT


def _clean_translation_output(text: str) -> str:
    cleaned = (text or "").strip()
    fenced = re.fullmatch(r"```(?:\w+)?\s*(.*?)\s*```", cleaned, re.DOTALL)
    if fenced:
        cleaned = fenced.group(1).strip()

    previous = None
    while previous != cleaned:
        previous = cleaned
        cleaned = TRANSLATION_PREFIX_RE.sub("", cleaned).strip()

    return cleaned


def _paragraphs(text: str):
    return [p.strip() for p in re.split(r"\n{2,}", text or "") if p.strip()]


def _escape_newlines_inside_json_strings(text: str) -> str:
    result = []
    in_string = False
    escaped = False

    for ch in text:
        if ch == '"' and not escaped:
            in_string = not in_string
            result.append(ch)
            continue

        if in_string and ch == '\n':
            result.append('\\n')
            escaped = False
            continue

        result.append(ch)

        if ch == '\\' and not escaped:
            escaped = True
        else:
            escaped = False

    return ''.join(result)


def _repair_concatenated_json_strings(text: str) -> str:
    return re.sub(r'"\s*\+\s*"', '', text)


def _has_required_article_keys(value) -> bool:
    return isinstance(value, dict) and all(k in value for k in REQUIRED_ARTICLE_KEYS)


def _parse_article_json(content_str: str) -> dict:
    last_error = None

    try:
        parsed = _parse_json_candidate(content_str)
        if _has_required_article_keys(parsed):
            return parsed
    except Exception as e:
        last_error = e

    fenced = re.search(r'```(?:json)?\s*(.*?)\s*```', content_str, re.DOTALL | re.IGNORECASE)
    if fenced:
        try:
            parsed = _parse_json_candidate(fenced.group(1))
            if _has_required_article_keys(parsed):
                return parsed
        except Exception as e:
            last_error = e

    sliced = _extract_first_balanced_json_object(content_str)
    if sliced:
        try:
            parsed = _parse_json_candidate(sliced)
            if _has_required_article_keys(parsed):
                return parsed
        except Exception as e:
            last_error = e

    if last_error:
        raise last_error
    raise ValueError("Failed to parse article JSON from model output.")


class _CleanArticleExtractor(HTMLParser):
    CONTENT_TAGS = {"p", "h2", "h3", "figcaption"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.current_tag = None
        self.current_parts = []
        self.blocks = []
        self.h1_values = []
        self.meta = {}
        self.images = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "meta":
            name = attrs_dict.get("name") or attrs_dict.get("property")
            content = attrs_dict.get("content")
            if name and content:
                self.meta[name.lower()] = content
            return
        if tag == "img" and attrs_dict.get("src"):
            self.images.append(attrs_dict["src"])
            return
        if tag == "h1" or tag in self.CONTENT_TAGS:
            self.current_tag = tag
            self.current_parts = []

    def handle_endtag(self, tag):
        if tag != self.current_tag:
            return

        text = " ".join(" ".join(self.current_parts).split())
        if text:
            if tag == "h1":
                self.h1_values.append(text)
            else:
                self.blocks.append(text)

        self.current_tag = None
        self.current_parts = []

    def handle_data(self, data):
        if self.current_tag:
            text = " ".join(data.split())
            if text:
                self.current_parts.append(text)


def _extract_article_fields_locally(clean_html: str) -> dict:
    parser = _CleanArticleExtractor()
    parser.feed(clean_html or "")

    title = (
        parser.meta.get("og:title")
        or parser.meta.get("twitter:title")
        or (parser.h1_values[0] if parser.h1_values else "")
    )
    image_url = (
        parser.meta.get("og:image")
        or parser.meta.get("twitter:image")
        or (parser.images[0] if parser.images else "")
    )

    seen = set()
    blocks = []
    normalized_title = " ".join(title.split()).lower()
    for block in parser.blocks:
        normalized = " ".join(block.split())
        if len(normalized) < 20:
            continue
        lowered = normalized.lower()
        if lowered == normalized_title or lowered in seen:
            continue
        seen.add(lowered)
        blocks.append(normalized)

    content = "\n\n".join(blocks).strip()
    if not title or not content:
        text = re.sub(r"<[^>]+>", " ", clean_html or "")
        text = unescape(" ".join(text.split()))
        if not title:
            title = text[:180].strip()
        if not content:
            content = text

    return {
        "title": title.strip(),
        "content": content.strip(),
        "image_url": image_url.strip(),
    }


def _split_text_chunks(text: str, max_chars: int = TRANSLATION_CHUNK_SIZE):
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text or "") if p.strip()]
    chunks = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            for start in range(0, len(paragraph), max_chars):
                chunks.append(paragraph[start:start + max_chars].strip())
            continue

        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) > max_chars and current:
            chunks.append(current.strip())
            current = paragraph
        else:
            current = candidate

    if current:
        chunks.append(current.strip())

    return chunks


def _tail_paragraph_context(text: str, count: int = TRANSLATION_CONTEXT_PARAGRAPHS):
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text or "") if p.strip()]
    return "\n\n".join(paragraphs[-count:]).strip()


def _has_required_story_keys(value) -> bool:
    return isinstance(value, dict) and all(k in value for k in REQUIRED_STORY_KEYS)


def _extract_first_balanced_json_object(text: str):
    start = text.find('{')
    if start == -1:
        return None

    in_string = False
    escaped = False
    depth = 0

    for i in range(start, len(text)):
        ch = text[i]

        if ch == '"' and not escaped:
            in_string = not in_string

        if not in_string:
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]

        if ch == '\\' and not escaped:
            escaped = True
        else:
            escaped = False

    return None


def _extract_between_markers(text: str, start_marker: str, end_markers):
    start = text.find(start_marker)
    if start == -1:
        return None
    start += len(start_marker)

    end_positions = []
    for marker in end_markers:
        idx = text.find(marker, start)
        if idx != -1:
            end_positions.append(idx)

    if end_positions:
        return text[start:min(end_positions)]

    return text[start:]


def _extract_story_fields_with_regex(text: str):
    found = {}

    pattern_normal = re.compile(
        r'"(?P<key>title|content|caption|image_prompt)"\s*:\s*"(?P<value>(?:\\.|[^"\\])*)"',
        re.DOTALL,
    )
    pattern_escaped = re.compile(
        r'\\"(?P<key>title|content|caption|image_prompt)\\"\s*:\s*\\"(?P<value>(?:\\\\.|[^\\"])*)\\"',
        re.DOTALL,
    )

    for pattern in (pattern_normal, pattern_escaped):
        for match in pattern.finditer(text):
            key = match.group("key")
            value = match.group("value")
            value = value.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
            found[key] = value

    if "title" not in found:
        v = _extract_between_markers(text, '"title": "', ['",\n "content"'])
        if v is not None:
            found["title"] = v

    if "content" not in found:
        v = _extract_between_markers(text, '"content": "', ['",\n "caption"', '\\",\\n \\"caption\\"'])
        if v is not None:
            found["content"] = v

    if "caption" not in found:
        v = _extract_between_markers(text, '"caption": "', ['",\n "image_prompt"', '\\",\\n \\"image_prompt\\"'])
        if v is not None:
            found["caption"] = v

    if "image_prompt" not in found:
        v = _extract_between_markers(text, '"image_prompt": "', ['"\n}', '"}'])
        if v is None:
            v = _extract_between_markers(text, '\\"image_prompt\\": \\"', ['\\"\\n}', '\\"}'])
        if v is not None:
            found["image_prompt"] = v

    for key, value in list(found.items()):
        value = value.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\').strip()
        if value.endswith('"'):
            value = value[:-1]
        found[key] = value

    if _has_required_story_keys(found):
        return found
    return None


def _parse_json_candidate(candidate: str):
    candidates = [
        candidate,
        _escape_newlines_inside_json_strings(candidate),
        _repair_concatenated_json_strings(candidate),
        _escape_newlines_inside_json_strings(_repair_concatenated_json_strings(candidate)),
    ]

    last_error = None
    for value in candidates:
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            last_error = e

    raise last_error


def _parse_story_json(content_str: str) -> dict:
    last_error = None

    try:
        parsed = _parse_json_candidate(content_str)
        if _has_required_story_keys(parsed):
            return parsed
    except Exception as e:
        last_error = e

    fenced = re.search(r'```(?:json)?\s*(.*?)\s*```', content_str, re.DOTALL | re.IGNORECASE)
    if fenced:
        try:
            parsed = _parse_json_candidate(fenced.group(1))
            if _has_required_story_keys(parsed):
                return parsed
        except Exception as e:
            last_error = e

    sliced = _extract_first_balanced_json_object(content_str)
    if sliced:
        try:
            parsed = _parse_json_candidate(sliced)
            if _has_required_story_keys(parsed):
                return parsed
        except Exception as e:
            last_error = e

    extracted = _extract_story_fields_with_regex(content_str)
    if extracted:
        return extracted

    if last_error:
        raise last_error
    raise ValueError("Failed to parse story JSON from model output.")


class NineRouterAI(BaseAI):
    def __init__(self, api_key, text_model, image_model, base_url="http://localhost:20128/v1"):
        self.api_key = api_key
        self.text_model = text_model
        self.image_model = image_model
        self.base_url = base_url.rstrip('/')

    def _post_json(self, url: str, headers: dict, data: dict):
        last_error = None

        for attempt in range(1, AI_MAX_ATTEMPTS + 1):
            try:
                response = requests.post(url, headers=headers, json=data, timeout=AI_REQUEST_TIMEOUT)
            except requests.RequestException as e:
                last_error = e
            else:
                if response.status_code not in TRANSIENT_STATUS_CODES:
                    response.raise_for_status()
                    return response

                last_error = requests.HTTPError(
                    f"{response.status_code} Server Error from AI endpoint: {response.text[:500]}",
                    response=response,
                )

            if attempt < AI_MAX_ATTEMPTS:
                time.sleep(min(2 ** (attempt - 1), 8))

        if isinstance(last_error, requests.HTTPError):
            raise last_error
        raise requests.HTTPError(f"AI request failed after {AI_MAX_ATTEMPTS} attempts: {last_error}")

    def _chat_text(self, prompt: str, system_prompt: str = None) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        data = {
            "model": self.text_model,
            "messages": messages,
            "temperature": TRANSLATION_TEMPERATURE,
            "stream": False
        }

        response = self._post_json(url, headers, data)
        result = response.json()
        try:
            content = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            raise ValueError(f"Unexpected AI response structure: {result}")
        if not content:
            raise ValueError("AI returned empty content.")
        return content.strip()

    def _translate_text(self, text: str, language: str, *, article_title: str = "", previous_translation_context: str = "") -> str:
        source_paragraph_count = len(_paragraphs(text))
        context_lines = []
        if article_title:
            context_lines.append(f"Article title: {article_title}")
        if previous_translation_context:
            context_lines.append(
                f"Previous translated context already written in {language}. Use it only to keep names, "
                "pronouns, terminology, tone, and style consistent. Do not repeat, rewrite, summarize, or "
                "include any part of this context in the output:\n"
                f"{previous_translation_context}"
            )

        context_block = "\n\n".join(context_lines)
        system_prompt = (
            "You are a deterministic translation engine, not a conversational assistant. Translate every "
            "translatable part of <source_text> into the exact target language supplied by the user. This "
            "includes narration, dialogue inside quotation marks, short replies, stage directions, captions, "
            "headings, and text that is already in a third language. Preserve only proper names, brand names, "
            "URLs, code, and numbers when appropriate. Never expose analysis, reasoning, self-correction, "
            "editorial notes, translation notes, comments, warnings, refusals, copyright text, policy text, "
            "summaries, explanations, labels, introductions, markdown fences, or closing comments. Never "
            "output source sentences beside their translations. Output only the final translated text."
        )
        prompt = (
            f"TARGET LANGUAGE (authoritative, preserve exactly as written): {language}\n\n"
            f"Source paragraph count: {source_paragraph_count}\n\n"
            f"Translate all content inside <source_text> into {language}. The source may contain mixed "
            "languages; translate every translatable sentence from every source language into the single "
            f"target language {language}.\n\n"
            "NON-NEGOTIABLE OUTPUT RULES:\n"
            f"- Output only the finished translation in {language}, with no prefix or suffix.\n"
            "- Translate every narration sentence and every quoted line of dialogue, including one-word or "
            "very short replies such as \"What?\", \"Yes\", \"No secrets\", or \"I'm learning\".\n"
            "- Quotation marks do not make text exempt from translation. Do not preserve English dialogue "
            "merely because it is quoted, recorded, displayed on screen, or presented as evidence.\n"
            "- Translate stage directions, labels that belong to the source article, and embedded passages "
            "written in a different language.\n"
            f"- Do not output any ordinary prose in English or another non-{language} language.\n"
            "- Never output internal notes or self-corrections. Forbidden output includes lines or fragments "
            "beginning with \"Note:\", \"Wait:\", \"Inconsistent:\", \"Correction:\", \"Translation:\", "
            "\"Here is\", \"//\", or bracketed editorial commentary.\n"
            "- Never apologize, refuse, discuss copyright or permission, or claim that translation is not "
            "possible. The source is user-provided and must be translated in full.\n"
            "- Never include both the source sentence and its translation.\n"
            "- Do not add facts, explanations, annotations, summaries, or commentary.\n"
            f"- Use exactly {language}; do not substitute a related language, dialect, or locale.\n"
            f"- The output must contain exactly {source_paragraph_count} paragraphs, matching the source paragraph order.\n"
            "- Keep only proper names, brand names, URLs, code, and numbers unchanged when appropriate.\n"
            "- Do not summarize, expand, omit, reorder, explain, sanitize, or rewrite the story.\n"
            "- If the source text is a title or headline, translate that title directly; do not make it catchier, shorter, longer, or different.\n"
            "- Preserve every event, fact, name, relationship, number, date, chronology, point of view, tense, and tone.\n"
            "- Keep the translated output as close as naturally possible to the source length and sentence-by-sentence structure.\n"
            "- Preserve paragraph breaks.\n"
            "- Translate relationship words naturally for the target language, but keep them consistent.\n\n"
            "SILENT FINAL CHECK (perform internally; never print this check):\n"
            "1. Verify every quoted dialogue line was translated.\n"
            "2. Verify no complete source-language sentence remains.\n"
            "3. Verify there are no notes, corrections, refusals, explanations, or analysis fragments.\n"
            f"4. Verify every reader-facing sentence is in {language}.\n"
            "5. Verify paragraph count and order match the source.\n\n"
            f"{context_block}\n\n"
            f"<source_text>\n{text}\n</source_text>"
        )
        return _clean_translation_output(self._chat_text(prompt, system_prompt=system_prompt))

    def _extract_article_chunked(self, clean_html: str, article_url: str, language: str) -> dict:
        fields = _extract_article_fields_locally(clean_html)
        if not fields["title"] or not fields["content"]:
            raise ValueError("Failed to extract article text locally before chunked localization.")

        return self.translate_article_fields(
            fields["title"],
            fields["content"],
            fields["image_url"],
            language,
        )

    def translate_article_fields(self, title: str, content: str, image_url: str = "", language: str = "Ukrainian") -> dict:
        translated_title = self._translate_text(title, language, article_title=title)
        translated_chunks = []
        previous_translation_context = ""
        for chunk in _split_text_chunks(content):
            translated_chunk = self._translate_text(
                chunk,
                language,
                article_title=translated_title,
                previous_translation_context=previous_translation_context,
            )
            translated_chunks.append(translated_chunk)
            previous_translation_context = _tail_paragraph_context(translated_chunk)

        return {
            "title": translated_title,
            "content": "\n\n".join(translated_chunks).strip(),
            "caption": "",
            "image_url": (image_url or "").strip(),
        }

    def generate_story(self, prompt: str) -> dict:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        system_prompt = (
            "You are a creative writer. Generate a story based on the user's prompt. "
            "Obey the user's mandatory target-language requirement for every reader-facing field. "
            "Do not switch to English or another language in title, content, caption, or caption CTA. "
            "Respond ONLY with a JSON object containing these keys: "
            "'title', 'content', 'caption', 'image_prompt'. "
            "The 'image_prompt' should be a descriptive prompt for an AI image generator."
        )
        data = {
            "model": self.text_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "stream": False
        }

        response = self._post_json(url, headers, data)

        try:
            result = response.json()
        except Exception:
            raise ValueError(f"AI API returned non-JSON response: {response.text}")

        try:
            content_str = result['choices'][0]['message']['content']
            if not content_str:
                raise ValueError("AI returned empty content.")
            return _parse_story_json(content_str)
        except (KeyError, IndexError):
            raise ValueError(f"Unexpected AI response structure: {result}")
        except Exception:
            raise ValueError(f"Failed to parse AI response as JSON. Raw content: {content_str}")

    def extract_article(self, clean_html: str, article_url: str, language: str = "Ukrainian") -> dict:
        if len(clean_html or "") > CHUNKED_ARTICLE_THRESHOLD:
            return self._extract_article_chunked(clean_html, article_url, language)

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        prompt = (
            "Extract a publish-ready article from the cleaned HTML below. "
            f"The mandatory target language is exactly: {language}. "
            f"Write every ordinary reader-facing word in title, content, caption, and caption CTA in {language} only. "
            "Do not normalize, replace, reinterpret, or substitute the supplied target language, and do not switch "
            "to English or any other language. "
            "Return ONLY a JSON object with keys: title, content, caption, image_url. "
            "title must be plain text. content must be the full article body suitable for WordPress. "
            "caption must be 300-500 words, cut from the article content itself, read like a continuous excerpt, "
            "end at a suspenseful cliffhanger before the resolution, and append a localized call-to-action meaning "
            "read more in the comments below. Do not summarize the article in caption. "
            "image_url must be the best absolute article image URL, or an empty string if none exists. "
            f"Before returning JSON, verify that title, content, caption, and the caption CTA are entirely in {language}.\n\n"
            f"URL: {article_url}\n\nCLEAN_HTML:\n{clean_html}"
        )
        data = {
            "model": self.text_model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "stream": False
        }

        response = self._post_json(url, headers, data)

        try:
            result = response.json()
            content_str = result['choices'][0]['message']['content']
            if not content_str:
                raise ValueError("AI returned empty content.")
            return _parse_article_json(content_str)
        except (KeyError, IndexError):
            raise ValueError(f"Unexpected AI response structure: {result}")
        except Exception:
            raise ValueError(f"Failed to parse AI article response as JSON. Raw content: {content_str}")

    def generate_image(self, image_prompt: str) -> str:
        url = f"{self.base_url}/images/generations"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        final_prompt = _build_styled_image_prompt(image_prompt)
        data = {
            "model": self.image_model,
            "prompt": final_prompt,
            "n": 1,
            "size": "auto",
            "quality": "auto",
            "background": "auto",
            "image_detail": "high",
            "output_format": "png"
        }

        response = self._post_json(url, headers, data)
        result = response.json()

        return result['data'][0]['url']
