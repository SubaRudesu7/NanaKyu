import re
from datetime import datetime

from .mikan import MikanSource
from .models import Episode
from .source import DataSource
from .storage import Storage
from .title_parser import parse_episode, parse_subgroup


def _to_local(dt_str: str) -> datetime | None:
    """把 ISO 时间字符串统一成本地 naive datetime；空串或解析失败返回 None。"""
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str)
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    return dt


def _is_full_set(title: str) -> bool:
    """标题含集数区间（如 [01-28] / - 28）视为全集类条目。"""
    return re.search(r"\d+\s*[-–—]\s*\d+", title) is not None


def _pick_representative(eps: list[Episode]) -> Episode:
    """组内选代表条目：优先全集类，否则最新发布一条。"""
    full = [e for e in eps if _is_full_set(e.title)]
    pool = full if full else eps
    return sorted(pool, key=lambda e: e.pub_date or "", reverse=True)[0]


def _dedup_latest(eps: list[Episode]) -> list[Episode]:
    """同一字幕组多版本只留最新发布一条。"""
    order = sorted(eps, key=lambda e: e.pub_date or "", reverse=True)
    seen: set[str] = set()
    out: list[Episode] = []
    for ep in order:
        sub = parse_subgroup(ep.title)
        if sub in seen:
            continue
        seen.add(sub)
        out.append(ep)
    return out


class Checker:
    """第 2 层核心逻辑：遍历清单查更新。

    - 只更 1 集：不走分组，直接给各字幕组磁力，流程结束。
    - 更了多集：按字幕组分组、磁力懒加载，走 LLM 选定；未指定集数默认给全集。
    """

    def __init__(self, storage: Storage, source: DataSource | None = None):
        self.storage = storage
        self.source = source or MikanSource()

    def check(self, subgroup: str | None = None) -> list[dict]:
        results: list[dict] = []
        animes = self.storage.load()
        for anime in animes:
            try:
                episodes = self.source.get_updates(anime, subgroup=subgroup)
            except Exception as e:
                print(f"[{anime.title}] 检测失败：{e}")
                continue
            if not episodes:
                continue
            last = _to_local(anime.last_update)
            new_eps = []
            for ep in episodes:
                pub = _to_local(ep.pub_date)
                if pub is None:
                    continue
                if last is not None and pub <= last:
                    break
                new_eps.append(ep)
            if not new_eps:
                continue

            # 按集数统计新的集数（只用于判 ==1 / >1）
            ep_nums: dict[int, list[Episode]] = {}
            for ep in new_eps:
                num = parse_episode(ep.title)
                if num is not None:
                    ep_nums.setdefault(num, []).append(ep)
            if not ep_nums:
                continue

            anime.last_update = new_eps[0].pub_date  # 写回本次新条目里最新发布那条的时间

            if len(ep_nums) == 1:
                # 特例：只更一集 → 不走分组，直接给磁力，流程结束
                single = _dedup_latest(next(iter(ep_nums.values())))
                subs = []
                for ep in single:
                    ep.magnet = self.source.get_magnet(ep)
                    subs.append({"name": parse_subgroup(ep.title), "episode": ep, "magnet": ep.magnet})
                results.append({"anime": anime, "new_count": 1, "mode": "direct", "subgroups": subs})
                continue

            # 更了多集 → 按字幕组分组，磁力懒加载，走 LLM 选定
            by_sub: dict[str, list[Episode]] = {}
            for ep in new_eps:
                sub = parse_subgroup(ep.title)
                if sub:
                    by_sub.setdefault(sub, []).append(ep)
            subs = [
                {"name": sub, "representative": _pick_representative(eps), "magnet": ""}
                for sub, eps in by_sub.items()
            ]
            results.append({
                "anime": anime,
                "new_count": len(ep_nums),
                "mode": "lazy",
                "subgroups": subs,
                "hint": "更新了多集，已按字幕组分组，磁力懒加载：请调用 LLM 选定字幕组，未指定集数时默认取该组全集",
            })
        self.storage.save(animes)
        return results
