import requests
from requests.auth import HTTPBasicAuth
import os
from publishers.base_pub import BasePublisher

class WordPressPublisher(BasePublisher):
    def __init__(self, url: str, username: str, app_password: str):
        self.url = url.rstrip('/')
        self.username = username
        self.app_password = app_password
        self.auth = HTTPBasicAuth(self.username, self.app_password)

    def upload_media(self, image_source: str) -> int:
        """Uploads an image to WP media library and returns the media ID."""
        url = f"{self.url}/wp-json/wp/v2/media"
        
        if image_source.startswith(('http://', 'https://')):
            # Download first
            temp_path = "temp_image_for_wp.png"
            resp = requests.get(image_source, timeout=30)
            resp.raise_for_status()
            with open(temp_path, "wb") as f:
                f.write(resp.content)
            file_path = temp_path
        else:
            file_path = image_source

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Image not found at {file_path}")

        filename = os.path.basename(file_path)
        with open(file_path, "rb") as img:
            headers = {
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "image/png"  # Adjust if needed
            }
            resp = requests.post(url, auth=self.auth, headers=headers, data=img, timeout=60)
            
        # Clean up temp file if created
        if image_source.startswith(('http://', 'https://')) and os.path.exists(temp_path):
            os.remove(temp_path)

        resp.raise_for_status()
        return resp.json()["id"]

    def publish(self, title: str, content: str, image_source: str) -> str:
        """Creates a post and returns the link."""
        media_id = None
        if image_source:
            try:
                media_id = self.upload_media(image_source)
            except Exception as e:
                print(f"Warning: Failed to upload featured image: {e}")

        url = f"{self.url}/wp-json/wp/v2/posts"
        data = {
            "title": title,
            "content": content,
            "status": "publish",
            "featured_media": media_id
        }
        
        resp = requests.post(url, auth=self.auth, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()["link"]
