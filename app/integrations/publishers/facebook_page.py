import requests


class FacebookPagePublisher:
    def __init__(self, page_id: str, access_token: str, graph_version: str = "v23.0"):
        self.page_id = str(page_id or "").strip()
        self.access_token = str(access_token or "").strip()
        self.graph_version = (graph_version or "v23.0").strip()
        self.base_url = f"https://graph.facebook.com/{self.graph_version}"

    def _post(self, path: str, data: dict, files=None) -> dict:
        url = f"{self.base_url}/{path.lstrip('/')}"
        payload = {**data, "access_token": self.access_token}
        kwargs = {"files": files} if files is not None else {}
        resp = requests.post(url, data=payload, timeout=30, **kwargs)
        try:
            body = resp.json()
        except Exception:
            body = {}

        if resp.status_code >= 400:
            raise Exception(f"Facebook API error {resp.status_code}: {resp.text[:300]}")
        return body

    def publish_photo_caption(self, caption: str, image_url: str) -> str:
        body = self._post(
            f"{self.page_id}/photos",
            {
                "url": image_url,
                "caption": caption,
                "published": "true",
            },
        )
        post_id = body.get("post_id") or body.get("id")
        if not post_id:
            raise Exception(f"Facebook API error: missing post id in response {body}")
        return post_id

    def publish_text(self, caption: str) -> str:
        body = self._post(
            f"{self.page_id}/feed",
            {
                "message": caption,
            },
        )
        post_id = body.get("id")
        if not post_id:
            raise Exception(f"Facebook API error: missing post id in response {body}")
        return post_id

    def publish_photo_file(self, caption: str, image_path: str) -> str:
        with open(image_path, 'rb') as source:
            body = self._post(f'{self.page_id}/photos',
                              {'caption': caption, 'published': 'true'},
                              files={'source': source})
        post_id = body.get('post_id') or body.get('id')
        if not post_id:
            raise ValueError('Facebook response is missing a post id')
        return post_id

    def comment_on_post(self, post_id: str, message: str) -> str:
        body = self._post(
            f"{post_id}/comments",
            {
                "message": message,
            },
        )
        comment_id = body.get("id")
        if not comment_id:
            raise Exception(f"Facebook API error: missing comment id in response {body}")
        return comment_id
