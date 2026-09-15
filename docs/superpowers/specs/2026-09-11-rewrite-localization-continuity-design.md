# Rewrite Localization and Continuity Design

## Goal

Improve the Rewrite Story workflow so output reads as native literary prose in the target language and remains consistent across long, chunked source stories.

## Scope

Only the rewrite workflow is in scope. Existing Generate Story, publishing, and UI behavior must remain unchanged.

## Current problems

- The current system prompt only requests output in `{language}`, which encourages literal translation and source-language sentence structure.
- Character names, gender, roles, and family relationships are not fixed before chunk processing.
- Each chunk is processed with limited long-range context, allowing characters such as a niece and a sibling to be conflated.
- There is no explicit instruction to check language-specific gender, case, declension, agreement, or conjugation.
- Title/caption generation does not explicitly require sentence-safe extraction and Unicode preservation.

## Design

### 1. Native-language system prompt

Replace the existing rewrite system prompt with a localized literary-writing instruction. It must require idiomatic prose, native cadence, native syntax, and avoidance of literal translation/calques. It must require grammatical agreement appropriate to the target language, including gender, case, declension, noun/adjective agreement, and verb conjugation where applicable.

The prompt must preserve dramatic intent, pacing, emotional beats, approximate length, and story facts while allowing refreshed phrasing, narration, and scenic detail. It must prohibit changing character roles, ages, biological gender, family relationships, or established names. It must instruct the model to output only the requested content.

### 2. Preflight Localization Cast Sheet

Before source chunk rewriting, call the AI once with the complete source to create a structured Cast Sheet/Entity Registry in the target language. The registry records, for each important entity:

- original and localized name;
- biological and grammatical gender where relevant;
- age or approximate age;
- family/social role;
- relationships and required pronouns/forms of address;
- key locations, time period, objects, and immutable story facts.

The response must be valid JSON. The service must parse it and fail clearly if it is empty, invalid, or missing required entity fields. The registry is immutable for the remainder of the rewrite job.

The Cast Sheet must use this contract:

```json
{
  "entities": [
    {
      "original_name": "...",
      "localized_name": "...",
      "gender": "...",
      "age": "...",
      "role": "...",
      "relationships": {},
      "pronouns": {},
      "forms_of_address": {}
    }
  ],
  "locations": [],
  "timeline": [],
  "objects": [],
  "immutable_facts": []
}
```

`entities` must be a non-empty array. Every entity must include non-empty
`original_name`, `localized_name`, `age` or `approximate_age`, `role`,
`relationships`, `pronouns`, and `forms_of_address`. `gender` is required when
the source or target language uses gendered forms; otherwise it must be an
explicit null or `not_applicable` value. The preflight request must include the
complete source content and source title. If the source is too large for the
configured AI context window, the job must fail clearly before chunk rewriting;
the service must not silently truncate the source used for the Cast Sheet.

### 3. Continuity State

Maintain a state object while processing chunks. It includes the immutable Cast Sheet plus:

- active characters;
- current location and timeline;
- relationships currently relevant;
- events already established;
- unresolved story threads;
- a concise summary of the last rewritten chunk.

After each chunk, update the state from the rewritten result before sending the next chunk. State updates must not alter the immutable identity/relationship fields in the Cast Sheet.

Because each rewrite response must contain prose only, state updates use a
separate structured AI request after every successful chunk. That request
receives the Cast Sheet, the current Continuity State, and the rewritten chunk,
and returns JSON containing the active characters, current location and
timeline, relevant relationships, established events, unresolved story
threads, and a concise summary of the rewritten chunk. Malformed or empty state
updates fail the job; state updates must never be appended to the story.

### 4. Chunk prompt

Every chunk request receives the system prompt, the fixed Cast Sheet, the current Continuity State, and the source chunk. The request must require a seamless continuation, explicit subject/pronoun control, exact application of localized names and relationships, target-language grammar polishing, and output of only the rewritten chunk.

### 5. Title and caption

After assembling the rewritten chunks, make a final metadata request for a new localized title and caption. Require strict JSON with only `title` and `caption`. The caption must be copied exactly from the story prefix, end at a complete sentence at an emotional suspense point, avoid cutting a word, preserve Unicode characters, and target approximately 40–70 words.

### 6. Validation and warnings

Retain existing non-empty and 70%–130% length checks. Add validation for:

- valid Cast Sheet JSON and required fields;
- valid title/caption JSON;
- caption being an exact story prefix;
- immutable cast identity and relationship consistency;
- no missing rewritten chunk content.

Missing or malformed Cast Sheet data, contradictory immutable identity or
relationship data, malformed title/caption JSON, empty metadata fields, empty
chunk output, and malformed or empty Continuity State updates must fail the job
rather than silently save unreliable content.

Non-critical continuity omissions, caption-prefix mismatches, captions that do
not end at a complete sentence, captions that cut a word, and captions outside
the approximate 40–70-word target should produce explicit warnings. If the
assembled story contains fewer than 40 words, the caption length target is not
achievable and must produce a warning rather than a failure. The caption must
still be a valid exact story prefix and must not cut a word or sentence.

## Files

Primary change: `app/domain/rewrite_engine.py`.

If the implementation becomes difficult to test or maintain, extract context parsing/validation into a focused module such as `app/domain/rewrite_context.py`. Do not refactor unrelated workflows.

## Testing

Add focused tests covering:

- native-language and anti-calque instructions being sent;
- Cast Sheet parsing and malformed-response failure;
- continuity state being passed to every chunk;
- preservation of niece/sibling identities and gendered names across chunks;
- title/caption JSON parsing;
- caption ending on a complete sentence and matching the story prefix;
- empty chunk/model response failure;
- existing length and caption warnings remaining compatible.

Run the existing test suite plus the new rewrite tests. Do not claim completion until all tests pass.

## Non-goals

- No changes to Generate Story prompts or publishing behavior.
- No UI redesign.
- No change to the AI provider interface beyond the additional rewrite calls and structured context needed by this workflow.
