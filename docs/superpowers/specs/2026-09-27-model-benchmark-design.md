# Model Translation Benchmark — Design

Date: 2026-09-27

## Purpose

Add a Model Benchmark page that compares response time for 2–5 text models from one saved AI account. Every model receives the same fixed English story excerpt and the same instruction to translate it into Polish. Requests run sequentially in the selected order. The page shows model, status, and elapsed seconds in the approved compact table layout. It does not show or retain translations.

## Operator flow

The operator opens Model Benchmark from the sidebar, chooses one saved AI account, and clicks **Fetch models**. The page gets the model list from that account's `/models` endpoint using the same model discovery logic as the AI account form. The server resolves the saved account configuration; the browser sends only the account ID and never needs to resubmit its API key. The operator selects 2–5 distinct model IDs from the returned list. Changing account clears the model selection. A read-only, collapsible preview shows the fixed sample and the fixed target language, Polish.

Clicking **Run benchmark** creates a background job and returns its ID immediately. The page polls the job and renders one row per model: `Waiting`, `Running`, `Success`, or `Error`; elapsed seconds appear once each request ends. The active row may show a live timer. Reloading or revisiting the page restores recent benchmark jobs and their saved rows. The table shows no translation text. It may show a brief safe error reason for a failed row. The operator can cancel an active benchmark; completed rows remain, and unstarted rows are marked cancelled.

## Benchmark behavior

- The server owns one immutable sample, identified as `ceo-ceremony-parts-1-2-v1`. Use the exact PART 1 and PART 2 text below; do not expand, summarize, or trim it. This replaces the earlier approximate 1,000-word target.
- All models use identical `system` and `user` messages, including the full sample and a Polish translation instruction. Names and story details are preserved by the instruction. This benchmark compares API response time, not literary quality.
- Requests are non-streaming and run one at a time. Start the timer immediately before calling the AI client and stop it when the response or error returns. Report elapsed wall time in seconds to two decimals; it includes any client-side scheduler wait and network time. Use the same saved AI account, base URL, API key, and timeout for each model. Do not add an automatic retry or fallback model, which would distort the measurement.
- A row is `Success` only when the API call returns without error and its text content is nonempty after trimming whitespace. `finish_reason="length"` still counts as success if text is nonempty; the benchmark deliberately does not grade completeness or language quality. An HTTP error, timeout, malformed response, or empty text is `Error`. Continue to the next selected model after an error.
- Keep results in the existing `Job` record with `workflow_type="model_benchmark"`: account ID, sample ID, selected model IDs, per-model status, elapsed time, and safe error reason. Never store the sample body, generated translation, or API key in job logs or outputs. The latest jobs can be reopened via the existing jobs API. On app restart, generic job recovery marks an interrupted job failed; completed row results stay saved. A rerun creates a new job.
- A benchmark job uses the existing workflow runner and cancellation path. It does not create a content draft or publish anything.

## Backend interfaces

- `GET /model-benchmarks/sample` returns `{id, source_language, target_language, word_count, text}` for the fixed sample preview.
- `GET /model-benchmarks/accounts/{account_id}/models` returns the discovered model list for a saved account of type `ai`. It reuses `fetch_ai_models` and returns no credentials.
- `POST /model-benchmarks` accepts `{account_id, model_ids}` with 2–5 distinct nonblank IDs, verifies the selected IDs are currently returned by that account, creates a queued job, and returns `{job_id, status}`. Reject missing/wrong-type accounts and invalid selections before creating a job.
- `GET /jobs/{id}` and `GET /jobs?workflow_type=model_benchmark` supply progress, rows, and history. `POST /jobs/{id}/cancel` cancels active work.

## UI and failure states

The approved layout is one setup card above one compact results table. The account selector filters to saved AI accounts. **Fetch models** gives loading, empty-list, and error feedback; selected models appear in order and cannot exceed five. **Run benchmark** is disabled outside the 2–5 range. A failed model row shows a safe error without hiding successful rows. The overall job is `success` if every row succeeds, `partial_success` if some succeed, `failed` if none succeed, and `cancelled` on cancellation. Refreshing the page preserves the most recent run through saved job data.

## Verification

Backend tests use a fake AI client and fake model-list response. Verify account scoping, 2–5 distinct model validation, exact sample and prompt reuse, sequential call order, independent elapsed timing, nonempty success rule, failure-continues behavior, safe outputs without translation or credentials, cancellation, and persisted rows after an interrupted run. The frontend must compile and lint; no frontend tests are required for this implementation.

## Fixed sample

```text
PART 1
At my husband’s CEO ceremony, his secretary kissed him in front of five hundred employees. When I ordered her to move away, my husband shoved me onto the floor and shouted, “Know your place!” The ballroom erupted in laughter. I stood, sent a single message, and whispered, “Dad… Take the stage.” Moments later, the chairman approached the microphone—and every trace of confidence vanished from my husband’s face.

The kiss lasted only three seconds, but it ended eight years of marriage in front of five hundred laughing employees.

When my husband pushed me onto the ballroom floor and roared, “Know your place,” I finally realized he had forgotten who had placed him on that stage in the first place.

Crystal chandeliers glowed above Whitmore Technologies’ annual leadership ceremony.

My husband, Ethan Bennett, stood beneath a gold banner announcing his appointment as the company’s new CEO. He smiled like a king waiting to receive his crown.

At his side stood his secretary, Madison Blake, dressed in a shimmering silver gown better suited to a nightclub than a corporate event.

She wore the satisfied expression of someone who believed she already knew how the evening would end.

The chairman had barely finished announcing Ethan’s promotion when Madison grabbed his face and kissed him.

The ballroom gasped.

Then Ethan kissed her back.

My fingers tightened around my champagne glass until they turned cold.

For months, Ethan had dismissed me as “domestic,” mocked the years I had spent studying corporate law, and told his colleagues that I lacked the courage required for business.

I allowed him to speak.

Arrogant men often reveal the most when they are convinced no intelligent person is listening.

I walked toward the stage.

Every camera in the room followed me.

“Step away from my husband,” I said.

Madison slowly wiped her lipstick from Ethan’s mouth with her thumb.

“Oh,” she purred. “You’re still here?”

Several executives laughed.

Ethan’s expression tightened.

“Natalie, don’t embarrass me tonight.”

“You embarrassed yourself.”

Madison rested against him.

“She really doesn’t understand how things work at this level.”

I stepped onto the first stair.

Ethan rushed down, grabbed my arm, and shoved me backward.

My heel snapped.

I struck the marble floor hard enough to force the air from my lungs.

“Know your place!” he shouted.

For one stunned moment, the entire ballroom fell silent.

Then Madison laughed.

A few others followed.

At first, their laughter sounded uneasy.

Then it grew louder when Ethan grinned.

Hundreds of employees watched me kneeling at the bottom of the stage while my husband stood above me accepting their amusement like applause.

He believed I was nothing more than the quiet wife who arranged dinners, remembered birthdays, and made herself invisible during company events.

He knew Chairman Richard Whitmore was my father.

But he believed my father and I were estranged.

He had never learned that our distance was an arrangement required by the family trust.

And he certainly did not know that every major corporate decision still passed across my desk.

I rose slowly.

Pain burned through my elbow, but my voice remained steady.

I pulled out my phone and typed three words.

Take the stage.

Then I looked toward the dark balcony overlooking the ballroom.

“Dad,” I whispered. “It’s time.”

The side doors opened.

Chairman Richard Whitmore entered, accompanied by the company’s general counsel and two members of the board.

He was seventy-one years old, silver-haired, and feared in corporate circles across three continents.

Ethan’s smile disappeared.

PART 2
My father did not look at me first.

His eyes went directly to Ethan’s hand.

The same hand that had just shoved me.

Ethan forced out a laugh.

“Continue the ceremony. Natalie has made an unfortunate scene.”

Madison crossed her arms.

“Security should remove her.”
```
