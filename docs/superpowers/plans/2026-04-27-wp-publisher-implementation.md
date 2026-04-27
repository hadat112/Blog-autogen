# WordPress Publisher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a WordPress REST API publisher that can upload media and create posts with featured images.

**Architecture:** A modular `BasePublisher` interface with a concrete `WordPressPublisher` implementation using the WordPress REST API and `requests` library.

**Tech Stack:** Python 3.10+, `requests`, `responses`, `pytest`.

---

### Task 1: Create Base Interface

**Files:**
- Create: `publishers/base_pub.py`

- [ ] **Step 1: Write BasePublisher class**
```python
from abc import ABC, abstractmethod

class BasePublisher(ABC):
    @abstractmethod
    def publish(self, title: str, content: str, image_source: str) -> str:
        """
        Publishes content to a platform.
        :param title: Post title.
        :param content: Post content (HTML or plain text).
        :param image_source: Local path or URL to an image.
        :return: Link to the published post.
        """
        pass
```

- [ ] **Step 2: Commit base interface**
```bash
git add publishers/base_pub.py
git commit -m "feat: add BasePublisher abstract class"
```

### Task 2: Implement WordPressPublisher Boilerplate

**Files:**
- Create: `publishers/wp_rest.py`
- Test: `tests/test_wp_rest.py`

- [ ] **Step 1: Write failing test for initialization**
```python
import pytest
from publishers.wp_rest import WordPressPublisher

def test_wp_publisher_init():
    wp = WordPressPublisher("https://example.com", "user", "pass")
    assert wp.url == "https://example.com"
    assert wp.username == "user"
    assert wp.app_password == "pass"
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_wp_rest.py`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement WordPressPublisher initialization**
```python
from publishers.base_pub import BasePublisher

class WordPressPublisher(BasePublisher):
    def __init__(self, url: str, username: str, app_password: str):
        self.url = url.rstrip('/')
        self.username = username
        self.app_password = app_password

    def publish(self, title: str, content: str, image_source: str) -> str:
        # To be implemented
        pass
```

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_wp_rest.py`

- [ ] **Step 5: Commit**
```bash
git add publishers/wp_rest.py tests/test_wp_rest.py
git commit -m "feat: init WordPressPublisher class"
```

### Task 3: Implement upload_media (Local Path)

**Files:**
- Modify: `publishers/wp_rest.py`
- Modify: `tests/test_wp_rest.py`

- [ ] **Step 1: Write failing test for local upload**
```python
import responses
import json

@responses.activate
def test_upload_media_local(tmp_path):
    wp = WordPressPublisher("https://example.com", "user", "pass")
    
    # Mock media upload
    responses.add(
        responses.POST,
        "https://example.com/wp-json/wp/v2/media",
        json={"id": 42},
        status=201
    )
    
    test_file = tmp_path / "test.jpg"
    test_file.write_text("fake image data")
    
    media_id = wp.upload_media(str(test_file))
    assert media_id == 42
    assert len(responses.calls) == 1
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_wp_rest.py`

- [ ] **Step 3: Implement upload_media**
```python
import requests
import os
from requests.auth import HTTPBasicAuth

# ... inside WordPressPublisher class ...
    def upload_media(self, image_source: str) -> int:
        if image_source.startswith(('http://', 'https://')):
            # URL logic in next task
            return self._upload_from_url(image_source)
        
        return self._upload_from_path(image_source)

    def _upload_from_path(self, path: str) -> int:
        filename = os.path.basename(path)
        with open(path, 'rb') as f:
            files = {'file': (filename, f)}
            headers = {
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
            response = requests.post(
                f"{self.url}/wp-json/wp/v2/media",
                auth=HTTPBasicAuth(self.username, self.app_password),
                files=files,
                headers=headers
            )
            response.raise_for_status()
            return response.json()['id']
```

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/test_wp_rest.py`

- [ ] **Step 5: Commit**
```bash
git add publishers/wp_rest.py tests/test_wp_rest.py
git commit -m "feat: implement local media upload for WP"
```

### Task 4: Implement upload_media (URL)

**Files:**
- Modify: `publishers/wp_rest.py`
- Modify: `tests/test_wp_rest.py`

- [ ] **Step 1: Write failing test for URL upload**
```python
@responses.activate
def test_upload_media_url():
    wp = WordPressPublisher("https://example.com", "user", "pass")
    
    # Mock image download
    responses.add(responses.GET, "https://remote.com/image.jpg", body=b"fake data", status=200)
    
    # Mock media upload
    responses.add(
        responses.POST,
        "https://example.com/wp-json/wp/v2/media",
        json={"id": 43},
        status=201
    )
    
    media_id = wp.upload_media("https://remote.com/image.jpg")
    assert media_id == 43
    assert len(responses.calls) == 2 # 1 download, 1 upload
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Implement URL upload logic**
```python
import tempfile

# ... inside WordPressPublisher class ...
    def _upload_from_url(self, url: str) -> int:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        filename = url.split('/')[-1] or "image.jpg"
        with tempfile.NamedTemporaryFile(delete=True) as tmp:
            for chunk in response.iter_content(chunk_size=8192):
                tmp.write(chunk)
            tmp.flush()
            return self._upload_from_path(tmp.name)
```
Wait, `self._upload_from_path` expects a path that has the correct extension for WP to detect MIME type if possible, or we need to pass the filename.
Revised implementation:
```python
    def _upload_from_url(self, url: str) -> int:
        response = requests.get(url)
        response.raise_for_status()
        
        filename = url.split('/')[-1] or "image.jpg"
        # We need the filename for Content-Disposition
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = os.path.join(tmpdir, filename)
            with open(tmp_path, 'wb') as f:
                f.write(response.content)
            return self._upload_from_path(tmp_path)
```

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**
```bash
git add publishers/wp_rest.py tests/test_wp_rest.py
git commit -m "feat: implement URL media upload for WP"
```

### Task 5: Implement publish method

**Files:**
- Modify: `publishers/wp_rest.py`
- Modify: `tests/test_wp_rest.py`

- [ ] **Step 1: Write failing test for publish**
```python
@responses.activate
def test_publish_success(tmp_path):
    wp = WordPressPublisher("https://example.com", "user", "pass")
    
    # Mock media upload
    responses.add(responses.POST, "https://example.com/wp-json/wp/v2/media", json={"id": 42}, status=201)
    
    # Mock post creation
    responses.add(
        responses.POST,
        "https://example.com/wp-json/wp/v2/posts",
        json={"link": "https://example.com/my-post"},
        status=201
    )
    
    test_file = tmp_path / "test.jpg"
    test_file.write_text("fake image data")
    
    link = wp.publish("My Title", "My Content", str(test_file))
    assert link == "https://example.com/my-post"
    
    # Verify post payload
    post_call = responses.calls[1]
    payload = json.loads(post_call.request.body)
    assert payload['title'] == "My Title"
    assert payload['content'] == "My Content"
    assert payload['featured_media'] == 42
    assert payload['status'] == "publish"
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Implement publish method**
```python
    def publish(self, title: str, content: str, image_source: str) -> str:
        media_id = self.upload_media(image_source)
        
        payload = {
            'title': title,
            'content': content,
            'status': 'publish',
            'featured_media': media_id
        }
        
        response = requests.post(
            f"{self.url}/wp-json/wp/v2/posts",
            auth=HTTPBasicAuth(self.username, self.app_password),
            json=payload
        )
        response.raise_for_status()
        return response.json()['link']
```

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit final implementation**
```bash
git add publishers/wp_rest.py tests/test_wp_rest.py
git commit -m "feat: complete WordPress REST API publisher implementation"
```
