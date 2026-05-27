from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from .result import PluginResult


ProgressEmitter = Callable[[int, str, int, str, Optional[str]], None]


@dataclass
class ArticlePayload:
    title: str
    content: str
    caption: str = ""
    image_url: str = ""
    source_url: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArticlePayload":
        return cls(
            title=(data.get("title") or "").strip(),
            content=(data.get("content") or "").strip(),
            caption=(data.get("caption") or "").strip(),
            image_url=(data.get("image_url") or "").strip(),
            source_url=(data.get("source_url") or "").strip(),
        )


@dataclass
class PipelineState:
    article: ArticlePayload
    disabled_steps: Set[str]
    language_name: str
    caption_cta: str
    log_task_id: str
    task_id: Optional[str] = None
    auto_caption: bool = True
    status: str = "Success"
    error_msg: str = ""
    status_note: Optional[str] = None
    notification_prefix_lines: List[str] = field(default_factory=list)
    wp_url: str = ""
    fb_post_id: str = ""
    fb_post_error: str = ""
    fb_comment_error: str = ""
    fb_comment_state: str = "skipped"
    plugin_results: List[PluginResult] = field(default_factory=list)

    def result_dict(self) -> Dict[str, Any]:
        final_status = self.status if self.status == "Success" else f"{self.status}: {self.error_msg}"
        if self.status_note and self.status == "Success":
            final_status = self.status_note

        return {
            "status": "success",
            "title": self.article.title,
            "url": self.wp_url,
            "outputs": {
                "wordpress_url": self.wp_url,
                "facebook_post_id": self.fb_post_id,
                "facebook_comment_state": self.fb_comment_state,
                "image_url": self.article.image_url,
                "final_status": final_status,
                "plugins": [
                    {
                        "name": result.name,
                        "status": result.status,
                        "output": result.output,
                        "error": result.error,
                    }
                    for result in self.plugin_results
                ],
            },
        }


@dataclass
class PipelinePorts:
    wp: Any = None
    wp_config: Optional[Dict[str, Any]] = None
    sheets: Any = None
    fb: Any = None
    tg_config: Optional[Dict[str, Any]] = None
    telegram_sender: Optional[Callable[[str, str, str], Any]] = None
    storage: Any = None
    image_mode: str = "direct"
