from time import monotonic

from app.domain.content_validation import caption_matches_prefix, parse_json_object
from app.integrations.ai.openai_compatible import _split_text_chunks


def normalize_target_quotes(text: str, language: str) -> str:
    lang = (language or "").strip().lower().replace("_", "-")
    if not text or not any(mark in text for mark in ('"', "“", "”", "„", "«", "»")):
        return text

    if lang in {
        "czech", "cs", "cesky", "čeština",
        "slovak", "sk", "slovenčina",
        "german", "de", "deutsch",
    }:
        open_q, close_q = "„", "“"
    elif lang in {"polish", "pl", "polski", "romanian", "ro", "română"}:
        open_q, close_q = "„", "”"
    elif lang in {"russian", "ru", "ukrainian", "uk", "french", "fr", "français"}:
        open_q, close_q = "«", "»"
    else:
        open_q, close_q = "“", "”"

    # Treat all common double-quote styles as quote boundaries, then emit one
    # target-language style. This also handles a caption that ends mid-dialogue.
    reconstructed = []
    inside_quote = False
    quote_marks = {'"', "“", "”", "„", "«", "»"}
    for char in text:
        if char not in quote_marks:
            reconstructed.append(char)
            continue
        reconstructed.append(close_q if inside_quote else open_q)
        inside_quote = not inside_quote
    return "".join(reconstructed)


REWRITE_SYSTEM_PROMPT = (
    "You are an accomplished dramatic fiction author. "
    "Create a substantially new dramatic story inspired by the supplied reference, written with native literary excellence in {language}.\n\n"
    "MANDATORY LOCALIZATION & WRITING RULES:\n"
    "1. NATIVE LITERARY PROSE: Write every reader-facing word in natural, idiomatic {language}. Avoid stiff literal translation, word-by-word calques, or English sentence structures. Use native cadence, authentic phrasing, and proper grammatical agreement (gender, case, declension, conjugation).\n"
    "2. STRICT REGISTER & FORMALITY CONSISTENCY: Maintain a strict, unwavering level of formality and grammatical address (e.g., Vykání vs Tykání in Czech/Slovak, Pan/Pani in Polish, Lei vs Tu in Italian, Siezen vs Duzen in German) between characters across all chunks. Never switch a character relationship from formal to informal (or vice versa) midway.\n"
    "3. CONSISTENT NATIVE PUNCTUATION: Consistently apply standard dialogue quotation marks and typographic punctuation for {language} (e.g., „...“ in Czech/German, „...” in Polish, « ... » in French, “...” in English). Never switch quotation styles across chunks.\n"
    "4. STORY FACTS & DRAMATIC INTENT: Preserve the dramatic intent, emotional beats, character relationships, and approximate length of the reference, but refresh phrasing, narration, and scenic details. Character identities and locations must remain consistent.\n"
    "5. OUTPUT ONLY: Return only the requested story prose without any preamble, notes, explanations, commentary, or conversational remarks."
)


def _history_messages(system_prompt, turns):
    """Build the complete rewrite conversation, including every source chunk."""
    messages = [{"role": "system", "content": system_prompt}]
    for source_chunk, rewritten in turns:
        messages.append({
            "role": "user",
            "content": (
                "Rewrite the following source chunk as the next continuous part of the new story. "
                "Output only the rewritten chunk.\n\n<source_chunk>\n"
                f"{source_chunk}\n</source_chunk>"
            ),
        })
        messages.append({"role": "assistant", "content": rewritten})
    return messages


class RewriteEngine:
    def __init__(self, ai_client, chunk_size=6000):
        self.ai = ai_client
        self.chunk_size = chunk_size
        self.recovery = None

    def rewrite(self, title, content, language, progress=None):
        chunks = self.recovery.get("rewrite:chunks") if self.recovery else None
        if chunks is None:
            chunks = _split_text_chunks(content, max_chars=self.chunk_size)
            if self.recovery:
                self.recovery.save("rewrite:chunks", chunks)
        if not chunks:
            raise ValueError("Source article has no content")
        translate_title = getattr(self.ai, "translate_title", None)
        translated_title = self.recovery.get("title") if self.recovery else None
        if translated_title is None:
            translated_title = translate_title(title, language) if callable(translate_title) else None
            if self.recovery and isinstance(translated_title, str):
                self.recovery.save("title", translated_title)
        system = REWRITE_SYSTEM_PROMPT.format(language=language)
        turns = []
        for index, chunk in enumerate(chunks, start=1):
            started_at = monotonic()
            if progress:
                progress(index, len(chunks), "rewriting", {"event": "start", "word_count": len(chunk.split())})
            messages = _history_messages(system, turns)
            messages.append({
                "role": "user",
                "content": (
                    f"Rewrite source chunk {index} of {len(chunks)} as the next continuous part of the new story in {language}. "
                    "Maintain seamless narrative continuity, consistent character address and formality (do not switch formal/informal registers), "
                    "and native dialogue quotation marks. Output only the rewritten chunk.\n\n<source_chunk>\n"
                    f"{chunk}\n</source_chunk>"
                ),
            })
            value = self.recovery.get(f"rewrite:chunk:{index}") if self.recovery else None
            if value is None:
                message = self.ai.chat(messages, temperature=0.7)
                value = (message.get("content") or "").strip()
            if not value:
                raise ValueError(f"AI returned an empty rewrite for chunk {index}")
            value = normalize_target_quotes(value, language)
            if self.recovery:
                self.recovery.save(f"rewrite:chunk:{index}", value)
            turns.append((chunk, value))
            if progress:
                progress(index, len(chunks), "rewriting", {
                    "event": "done",
                    "word_count": len(chunk.split()),
                    "elapsed_ms": round((monotonic() - started_at) * 1000),
                })

        story = "\n\n".join(rewritten for _, rewritten in turns).strip()
        if progress:
            progress(len(chunks), len(chunks), "metadata", None)
        final_messages = _history_messages(system, turns)
        final_messages.append({
            "role": "user",
            "content": (
                "Return JSON only with caption. Caption must be copied exactly "
                "from the beginning of the assembled story and stop at a suspenseful point. "
                f"Original reference title: {title}"
            ),
        })
        metadata = self.recovery.get("rewrite:metadata") if self.recovery else None
        if metadata is None:
            metadata = parse_json_object(self.ai.chat(final_messages, temperature=0.5).get("content"))
        new_title = str(metadata.get("title") or "").strip()
        final_title = translated_title or new_title
        caption = str(metadata.get("caption") or "").strip()
        caption = normalize_target_quotes(caption, language)
        if not final_title:
            raise ValueError("AI returned an empty translated title")
        if not caption:
            raise ValueError("AI returned an empty rewritten caption")
        if self.recovery:
            self.recovery.save("rewrite:metadata", metadata)
        caption_match = caption_matches_prefix(story, caption)
        original_words = max(1, len((content or "").split()))
        ratio = len(story.split()) / original_words
        warnings = [] if 0.7 <= ratio <= 1.3 else ["Rewritten length is outside 70%–130% of the source"]
        if not caption_match:
            warnings.append("Caption differs from story opening")
        return {
            "title": final_title,
            "content": story,
            "caption": caption,
            "caption_matches_prefix": caption_match,
            "warnings": warnings,
        }
