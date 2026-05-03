import argparse
from dataclasses import dataclass
from typing import Optional


@dataclass
class RunOptions:
    limit: Optional[int]
    threads: int
    language: str
    debug: bool
    update: bool = False
    with_image: bool = False
    no_image: bool = False

    def resolve_enable_image(self, default_from_config: bool) -> bool:
        if self.with_image and self.no_image:
            raise ValueError("--with-image and --no-image cannot be used together")
        if self.no_image:
            return False
        if self.with_image:
            return True
        return bool(default_from_config)


def parse_run_tokens(tokens: list[str]) -> RunOptions:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--threads", type=int, default=5)
    parser.add_argument("--language", type=str, default="Ukraina")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--with-image", action="store_true")
    parser.add_argument("--no-image", action="store_true")

    ns = parser.parse_args(tokens)

    if ns.with_image and ns.no_image:
        raise ValueError("--with-image and --no-image cannot be used together")

    return RunOptions(
        limit=ns.limit,
        threads=ns.threads,
        language=ns.language,
        debug=ns.debug,
        update=ns.update,
        with_image=ns.with_image,
        no_image=ns.no_image,
    )
