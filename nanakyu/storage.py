import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .models import Anime


class Storage:
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

    def add(self, anime: Anime) -> bool:
        animes = self.load()
        if any(a.bangumi_id == anime.bangumi_id for a in animes):
            return False            
        if not anime.added_at:
            anime.added_at = datetime.now(timezone.utc).isoformat()
        animes.append(anime)
        self.save(animes)
        return True

    def remove(self, bangumi_id: str) -> bool:
        animes = self.load()
        kept = [a for a in animes if a.bangumi_id != bangumi_id]
        if len(kept) == len(animes):
            return False           
        self.save(kept)
        return True

    def get(self, bangumi_id: str) -> Anime | None:
        for a in self.load():
            if a.bangumi_id == bangumi_id:
                return a
        return None
