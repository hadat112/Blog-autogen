# WordPress publish without a featured image

## Goal

If a draft's remote or local image cannot be uploaded to WordPress, continue publishing the article without a featured image. The image failure must be visible as a warning, while the article remains a successful WordPress publication.

## Design

In `WordPressPublishingService.publish`, isolate the image-upload operation from post creation. Catch upload failures only around `upload_remote` and `upload_file`, log a warning containing the draft ID and sanitized failure message, and continue with `media_id = None`. The existing post-creation exception handling remains unchanged so ambiguous or failed WordPress post creation still produces its current terminal states.

When `media_id` is `None`, `WordPressDestinationGateway.create_post` already omits `featured_media` from the REST payload. A successfully created draft therefore has `state = "wordpress_created"` and an empty `wp_media_id`.

## Error handling

- Image download, DNS, proxy, validation, and image-upload errors are non-fatal.
- Post creation errors remain fatal and preserve the existing `publish_unknown`/`publish_failed` behavior.
- Warnings are emitted through the application logger; no database migration or API schema change is required.

## Tests

Add a service test with a gateway whose image upload raises an exception. Assert that `create_post` is still called with `media_id=None` and that the draft reaches `wordpress_created` without a media ID. Preserve the existing successful-upload and post-failure tests.
