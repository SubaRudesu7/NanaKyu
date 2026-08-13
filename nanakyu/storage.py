import json
import os
import tempfile
from pathlib import Path

from .models import Anime


class Storage:
    """本地 JSON 存储：记录订阅番的 last_update 跟踪表。"""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[Anime]:
        if not self.path.exists():
            return []
        with open(self.path, encoding="utf-8") as f:
            raw = json.load(f)
        return [Anime.from_dict(item) for item in raw.get("animes", [])]

    def save(self, animes: list[Anime]) -> None:
        payload = {"version": 1, "animes": [a.to_dict() for a in animes]}
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)
