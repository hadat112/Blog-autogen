# Design Spec: WordPress Publisher Implementation

## 1. Overview
This specification details the implementation of the `BasePublisher` abstract class and its first concrete implementation, `WordPressPublisher`, using the WordPress REST API. This module will allow the AI Story Automation tool to distribute content directly to WordPress sites.

## 2. Class Definitions

### 2.1 `BasePublisher` (publishers/base_pub.py)
- **Purpose:** Define a consistent interface for all future publishing platforms (e.g., Facebook, Instagram).
- **Interface:**
    - `publish(title: str, content: str, image_source: str) -> str`: Abstract method.
    - `image_source` can be a local file path or a remote URL.
    - Returns the URL of the published post.

### 2.2 `WordPressPublisher` (publishers/wp_rest.py)
- **Inherits from:** `BasePublisher`
- **Constructor:** `__init__(url: str, username: str, app_password: str)`
    - `url`: Base URL of the WordPress site (e.g., `https://example.com`).
    - `username`: WP User with publishing permissions.
    - `app_password`: Generated Application Password.
- **Internal Helper:** `upload_media(image_source: str) -> int`
    - Logic:
        1. If `image_source` starts with `http://` or `https://`:
            - Download the file to a temporary location using `tempfile`.
            - Use the original filename from the URL if possible.
        2. Read the file (local or temp) in binary mode.
        3. POST to `/wp-json/wp/v2/media`.
        4. Headers: `Content-Disposition: attachment; filename="..."`.
        5. Return the `id` of the uploaded media.
- **Public Method:** `publish(title: str, content: str, image_source: str) -> str`
    - Logic:
        1. Call `upload_media(image_source)` to get `media_id`.
        2. POST to `/wp-json/wp/v2/posts`.
        3. Payload:
            - `title`: Post title.
            - `content`: Post HTML content.
            - `status`: 'publish'.
            - `featured_media`: `media_id`.
        4. Return the `link` field from the API response.

## 3. Technical Implementation
- **HTTP Client:** `requests` (as found in `requirements.txt`).
- **Authentication:** HTTP Basic Authentication (`auth=(username, app_password)`).
- **Endpoints:**
    - Media: `POST {url}/wp-json/wp/v2/media`
    - Posts: `POST {url}/wp-json/wp/v2/posts`
- **MIME Types:** Basic detection based on file extension for the media upload.

## 4. Testing Strategy
- **Mocking:** Use the `responses` library to mock WordPress API endpoints.
- **Unit Tests (`tests/test_wp_rest.py`):**
    - `test_upload_media_local`: Verify local file upload logic.
    - `test_upload_media_url`: Verify download-then-upload logic.
    - `test_publish_success`: Verify full flow and payload structure.
    - `test_api_error_handling`: Verify behavior when WP returns non-200/201 status codes.

## 5. Approaches Considered

### Approach A: Sequential Implementation (Recommended)
- **Description:** Implement as a single synchronous class.
- **Pros:** simple, easy to test, fits the current `ThreadPoolExecutor` architecture.
- **Cons:** None significant for the current scope.

### Approach B: Async Implementation
- **Description:** Use `httpx` or `aiohttp` for non-blocking I/O.
- **Pros:** Higher throughput.
- **Cons:** Project currently uses `requests` and threading; introducing async adds complexity and potential dependency conflicts.

### Approach C: Plugin-based URL Upload
- **Description:** Use a WP plugin that allows creating media from a URL directly.
- **Pros:** Saves local bandwidth/temp storage.
- **Cons:** Requires user to install specific plugins; less portable.

**Decision:** Approach A is selected for its reliability and zero-dependency (on WP side) nature.
