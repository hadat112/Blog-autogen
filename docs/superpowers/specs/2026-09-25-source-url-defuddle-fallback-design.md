# Source URL Cleanup and Defuddle Fallback

## Goal

Normalize incoming source URLs by removing Facebook `fbclid` tracking parameters and add Defuddle as a fallback when WordPress REST extraction cannot provide usable article content.

## Scope

- Normalize `source_url` in the frontend before workflow requests.
- Keep backend normalization defensive so requests from other clients are also cleaned before persistence and fetching.
- Preserve the existing WordPress REST path as the primary source.
- Call the Defuddle hosted API only when WordPress REST fails, returns no article, or returns missing/too-short title or content.
- Normalize Defuddle output into the existing source article shape.
- Support an optional `DEFUDDLE_API_KEY`; unauthenticated requests use the hosted free quota.

## Data flow

```text
Frontend URL input
  -> remove fbclid
  -> workflow API
  -> backend normalize_source_url
  -> WordPress REST extraction
  -> if unusable: Defuddle hosted API
  -> common SourceArticle payload
```

## URL normalization

Use the URL parser rather than string replacement. Remove only the `fbclid` query parameter and preserve all other query parameters, path, fragment behavior, and URL validity rules already enforced by the backend. The normalized URL is used for requests, persistence, deduplication, and displayed source links.

## Defuddle fallback

The fallback calls `https://defuddle.md/<clean-source-url>` using the existing HTTP client. If `DEFUDDLE_API_KEY` is configured, send it as a Bearer token. The response is Markdown with YAML frontmatter; parse the frontmatter and body into the existing title/content/image/language/source fields. Do not call Defuddle when WordPress REST has usable content.

If Defuddle also fails or returns unusable content, preserve the existing failure behavior and error reporting. Never log the API key or full tracking-bearing URL.

## Testing

- Frontend removes `fbclid` while preserving unrelated parameters.
- Backend normalization removes `fbclid`.
- Successful REST extraction does not call Defuddle.
- REST failure, missing article, empty content, and too-short content invoke Defuddle.
- Defuddle output is mapped to the existing source article contract.
- Defuddle failure preserves the existing error path.
- Optional API key is sent only when configured.

## Non-goals

- Reimplementing Defuddle in Python.
- Replacing WordPress REST as the primary source.
- Adding a new persistent setting or frontend control for the Defuddle API key.
