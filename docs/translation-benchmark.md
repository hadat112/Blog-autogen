# Translation Benchmark

The Translation Benchmark screen compares two or more configured AI accounts
without changing the production pipeline.

## Run A Benchmark

1. Create one AI account per model or provider configuration.
2. Open `Benchmarks` in the sidebar.
3. Select at least two AI accounts.
4. Select the target language.
5. Choose:
   - `Standard suite`: three fixed English cases covering dialogue, relationships,
     dates, numbers, currencies, and paragraph continuity.
   - `Custom article`: one user-provided title and article body.
6. Click `Run benchmark`.

The run continues in the background. The page polls the API and displays partial
progress until all candidates finish.

## Fairness Rules

- Every candidate receives the same source cases and translation prompt.
- Candidates run independently.
- Each HTTP request has one attempt. There is no semantic or transport retry.
- Candidate labels are hidden by default for blind review.
- Model names can be revealed after manual review.

## Result Metrics

The hard score checks:

- Empty or refusal output.
- Paragraph preservation.
- Number, date, and currency preservation.
- Abnormal output length.
- Translation prefixes and likely source-text leakage.
- Request count, token usage when returned by the provider, and latency.

The hard score does not reliably measure fluency, cultural localization, or
semantic nuance. Use the blind output comparison and manual 1-5 rating for those
qualities.

For production selection, first exclude candidates with invalid outputs, then
compare manual quality, latency, and token usage.

## Current Implementation Status

The detailed implementation handoff, known limitations, verification status,
and next steps are documented in:

```text
docs/translation-benchmark-handoff.vi.md
```
