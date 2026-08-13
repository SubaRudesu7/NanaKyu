from datetime import datetime

from .models import Anime, Episode
from .source import DataSource
from .storage import Storage


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


class Checker:
    """第 2 层核心逻辑：订阅来自蜜柑账号，本地只记 last_update 阈值。

    - 订阅列表 = source.list_subscriptions()（MyBangumi 账号的订阅番）
    - 每部番只取订阅字幕组的条目（get_updates 已过滤）
    - 比 last_update 新的条目 = 新集，直接给磁力
    """

    def __init__(self, source: DataSource, storage: Storage):
        self.source = source
        self.storage = storage

    def check(self) -> list[dict]:
        results: list[dict] = []
        subscriptions = self.source.list_subscriptions()

        # 本地跟踪表：bangumi_id → Anime（含 last_update）
        tracking = {a.bangumi_id: a for a in self.storage.load()}

        for anime in subscriptions:
            # 补齐本地跟踪记录
            rec = tracking.get(anime.bangumi_id)
            if rec is None:
                rec = Anime(bangumi_id=anime.bangumi_id, title=anime.title)
                tracking[anime.bangumi_id] = rec

            try:
                episodes = self.source.get_updates(anime)
            except Exception as e:
                print(f"[{anime.title}] 检测失败：{e}")
                continue
            if not episodes:
                continue

            last = _to_local(rec.last_update)
            new_eps = []
            for ep in episodes:
                pub = _to_local(ep.pub_date)
                if pub is None:
                    continue
                if last is not None and pub <= last:
                    break  # 已按时间倒序，遇到不再新的就停
                new_eps.append(ep)
            if not new_eps:
                continue

            # 写回本次新条目里最新发布那条的时间，供下次比较
            rec.last_update = new_eps[0].pub_date

            for ep in new_eps:
                results.append({"anime": anime, "episode": ep, "magnet": ep.magnet})

        # 落盘跟踪表
        self.storage.save(list(tracking.values()))
        return results
