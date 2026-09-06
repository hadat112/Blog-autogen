from app.domain.content_validation import caption_matches_prefix, parse_json_object
from app.integrations.ai.openai_compatible import _split_text_chunks


REWRITE_SYSTEM_PROMPT = (
    "Create a substantially new dramatic story inspired by the supplied reference. "
    "Write every reader-facing word in {language}. Preserve the dramatic intent and approximate length, "
    "but change phrasing, narration, and details; names and locations may change consistently. "
    "Return only the requested content, without analysis or policy commentary."
)


def _history_messages(system_prompt, rewritten_chunks):
    messages = [{"role": "system", "content": system_prompt}]
    for index, rewritten in enumerate(rewritten_chunks):
        messages.append({
            "role": "user",
            "content": "Begin the rewritten story." if index == 0 else "Continue.",
        })
        messages.append({"role": "assistant", "content": rewritten})
    return messages


class RewriteEngine:
    def __init__(self, ai_client, chunk_size=6000):
        self.ai = ai_client
        self.chunk_size = chunk_size

    def rewrite(self, title, content, language, progress=None):
        chunks = _split_text_chunks(content, max_chars=self.chunk_size)
        if not chunks:
            raise ValueError("Source article has no content")
        system = REWRITE_SYSTEM_PROMPT.format(language=language)
        rewritten = []
        for index, chunk in enumerate(chunks, start=1):
            if progress:
                progress(index, len(chunks), "rewriting")
            messages = _history_messages(system, rewritten)
            messages.append({
                "role": "user",
                "content": (
                    f"Rewrite source chunk {index} of {len(chunks)} as the next continuous part of the new story. "
                    "Output only the rewritten chunk.\n\n<source_chunk>\n"
                    f"{chunk}\n</source_chunk>"
                ),
            })
            message = self.ai.chat(messages, temperature=0.7)
            value = (message.get("content") or "").strip()
            if not value:
                raise ValueError(f"AI returned an empty rewrite for chunk {index}")
            rewritten.append(value)

        story = "\n\n".join(rewritten).strip()
        final_messages = _history_messages(system, rewritten)
        final_messages.append({
            "role": "user",
            "content": (
                "Return JSON only with title and caption. Create a new title. Caption must be copied exactly "
                "from the beginning of the assembled story and stop at a suspenseful point. "
                f"Original reference title: {title}"
            ),
        })
        metadata = parse_json_object(self.ai.chat(final_messages, temperature=0.5).get("content"))
        new_title = str(metadata.get("title") or "").strip()
        caption = str(metadata.get("caption") or "").strip()
        if not new_title:
            raise ValueError("AI returned an empty rewritten title")
        if not caption:
            raise ValueError("AI returned an empty rewritten caption")
        caption_match = caption_matches_prefix(story, caption)
        original_words = max(1, len((content or "").split()))
        ratio = len(story.split()) / original_words
        warnings = [] if 0.7 <= ratio <= 1.3 else ["Rewritten length is outside 70%–130% of the source"]
        if not caption_match:
            warnings.append("Caption differs from story opening")
        return {
            "title": new_title,
            "content": story,
            "caption": caption,
            "caption_matches_prefix": caption_match,
            "warnings": warnings,
        }
