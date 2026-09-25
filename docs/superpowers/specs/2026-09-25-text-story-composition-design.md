# Text Story Composition — Design

Date: 2026-09-25

## Purpose

Add a dedicated page that turns a pasted source story into a short suspenseful rewrite and a complete WordPress-ready story. The workflow follows the intent of `docs/rewrite.md` and `docs/enhance.md`, using the selected pipeline language instead of the rewrite prompt's fixed English instruction. It produces four reviewable artifacts: the short rewrite, a title, the complete story, and an image-generation prompt that the operator can copy. It does not generate an image or publish automatically.

## Decisions

- The continuation follows the 550–650-word rewrite, not the pasted source story.
- The workflow runs automatically through four separate model requests: rewrite, title, image prompt, continuation. The title and image prompt are derived from the short rewrite to avoid resending the much longer complete story.
- The rewrite and enhance instructions remain separate user messages in the conversation history used for continuation. The model returns only the new continuation; application code prepends the saved rewrite exactly once.
- The continuation is produced in one model response. The workflow does not divide it into separately authored scenes. A provider/model unable to complete that response fails clearly rather than silently truncating or splitting it.
- All reader-facing outputs use the selected pipeline language. The image prompt is stored as text for copying; the existing draft editor remains responsible for optional image URL or upload.
- The operator reviews and may edit the draft before using the existing WordPress draft/publish controls.

## Page and operator flow

Add a sidebar entry and route for a new Text Story page. Reuse the Generate Story page's two-column structure. On desktop, a sticky left column contains a pipeline selector, a large source-story textarea, the Run control, and a four-step progress timeline. The right column exposes outputs as they become available: a copyable short rewrite, the title in the review editor, a copyable image prompt, and the complete story in the existing `DraftEditor`. On narrow screens, the columns stack in that order. A page-specific draft history lets the operator reopen earlier runs, including partial and failed runs.

Only active pipelines with an AI account and a WordPress account are selectable. The selected pipeline supplies the target language, AI account, WordPress account, and default category. Starting a run saves the source story before any model call. The page polls the job and draft as the existing Generate Story page does. The WordPress controls stay unavailable until the draft reaches `ready_for_review`; generation never triggers publication.

The page shows the image prompt in a separate read-only copy field. This field is not WordPress content and is not sent to the image-generation endpoint. The operator can supply a featured image through `DraftEditor` later.

## Workflow and model messages

The server owns a versioned set of prompt templates adapted from `docs/rewrite.md` and `docs/enhance.md`. It substitutes the pipeline language consistently, while preserving the key content requirements: a cinematic 550–650-word rewrite ending at a cliffhanger, and a 3,000–3,500-word concluding continuation. Runtime behavior must not depend on the operator's local copy of the Markdown files changing during an active job; each job records the prompt-template version it used.

1. **Rewrite request.** Send the pasted source story and the adapted rewrite instruction. Save the returned text as `rewrite_text` immediately. Keep the rewrite exactly as returned after surrounding-whitespace normalization. Its terminal continuation-style line and emoji, if produced by the prompt, remain part of the rewrite and therefore part of the complete story.
2. **Title request.** Send the saved rewrite plus a short title instruction. Save one plain-text title in the pipeline language. It should describe the opening conflict without spoiling the resolution.
3. **Image-prompt request.** Send the saved rewrite plus an instruction for one copyable image prompt depicting a concrete, visually coherent moment from the opening. Save the prompt as text. This request does not generate an image.
4. **Continuation request.** Build a manual conversation history in order: the original source story with the rewrite instruction, the model's saved rewrite as an assistant message, and the adapted enhance instruction as a new user message. The enhance message explicitly identifies the immediately preceding rewrite as the story to continue. It requests only the new 3,000–3,500-word continuation, beginning at the rewrite's final moment. It does not request the model to reproduce the rewrite. Title and image-prompt outputs are excluded from this history so they cannot steer the plot. Save the continuation separately, then set draft content to `rewrite_text + "\n\n" + continuation_text`.

The caption is cut in application code from the beginning of `rewrite_text` at a sentence boundary, approximately 45–70 words, and must be an exact prefix of complete draft content. The title comes from request 2. The image prompt remains separate from `ContentDraft.content` and the WordPress post body.

## Persistence and interfaces

Add a dedicated composition record linked one-to-one to `ContentDraft`. It stores `source_text`, `rewrite_text`, `continuation_text`, `image_prompt`, prompt-template version, and per-stage completion state. The existing draft stores the publishable title, complete content, caption, language, category, WordPress fields, and overall state. Use a distinct draft `kind` and job `workflow_type` for filtering, recovery links, and history. Job logs and outputs contain step names, timing, safe errors, and record identifiers, never full source or generated prose.

Add a start endpoint that accepts pipeline ID and source text, returns job and draft IDs, and launches a background workflow. Add a read endpoint for the composition artifacts and a retry endpoint for incomplete jobs. Retry resumes at the first incomplete or invalid stage using saved artifacts; it must not rerun completed requests or overwrite operator edits. A cancelled job retains all completed artifacts and can be retried. Deleting an unpublished draft removes its linked composition record. Extend the existing draft-kind schema and WordPress publish mapping so this new draft uses the same `DraftEditor` and `WordPressPublishingService` path as Generate Story.

## Validation and failure behavior

- Reject empty source text and any request that exceeds the configured model/provider context or expected output budget when those limits are known. Never silently trim source text. If provider limits are unavailable, report that capacity is unverified and check the response completion signal after each request.
- For every request, capture model, elapsed time, token usage when supplied, and completion/finish reason when supplied. Treat a reported length-limit or incomplete finish as failure even when nonempty text exists. Do not persist a truncated result as a completed stage.
- Rewrite must contain 550–650 whitespace-delimited words and end at a sentence boundary. Title and image prompt must be nonempty plain text. Request them in the pipeline language; automatic language detection on very short fields is not a reliable hard gate, so their language remains visible for operator review.
- Continuation must contain at least 3,000 whitespace-delimited words, begin as a continuation rather than by restating the rewrite, and end at a sentence boundary. More than 3,500 words produces a review warning. Check for a substantial copied prefix or duplicate paragraphs before assembly. The application cannot prove narrative consistency mechanically; the review step remains required.
- A failed stage leaves the draft in `generation_failed` with the saved artifacts intact and a safe, actionable error. Only a validated full story and title move it to `ready_for_review`. A failed title or image prompt may be retried independently; a failed continuation resumes from the saved rewrite, title, and image prompt.
- The UI displays stage-specific status and any warning. There is no automatic WordPress publication or automatic image generation.

## Verification

Use fake AI responses to verify four requests occur in the agreed order; title and image prompt requests receive the short rewrite rather than complete story; the continuation history has distinct rewrite and enhance user messages with the saved assistant rewrite between them; the assembled story contains the rewrite verbatim exactly once; and caption is an exact prefix. Cover incomplete/length-limited responses, invalid word counts, cancellation, retry from each stage, and preservation of completed artifacts. Add an API/UI workflow check that the new draft appears in page-specific history, can be reviewed and edited, and reaches the existing WordPress draft/publish service without automatic publication.

## Scope boundaries

The feature does not modify the existing Generate Story agent, V1 translation, or V2 article rewrite flows. It does not introduce Responses API-only behavior, split the continuation into scenes, generate an actual image, or automatically publish to WordPress.
