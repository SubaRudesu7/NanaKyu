"""废案"""


import re
from html import unescape
from xml.etree import ElementTree as ET

import requests

from ..data.models import Anime, Episode
from .base import DataSource

BASE_URL = "https://mikanani.kas.pub"


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class MikanSource(DataSource):
    """蜜柑计划数据源：搜索 / RSS 检测更新 / 单集页取磁力。"""

    def __init__(self, base_url: str = BASE_URL, timeout: int = 20):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})

    # ---------- 搜索 ----------

    def search(self, keyword: str) -> list[Anime]:
        resp = self.session.get(
            f"{self.base_url}/Home/Search",
            params={"searchstr": keyword},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        html = resp.text

        results: list[Anime] = []
        # 每条结果：<a href="/Home/Bangumi/{id}"> ... <div class="an-text" title="标题">
        for m in re.finditer(r'href="/Home/Bangumi/(\d+)"', html):
            bangumi_id = m.group(1)
            # 取本条目片段，到下一个条目为止，从中抠标题
            seg = html[m.start():m.start() + 800]
            tm = re.search(r'class="an-text"[^>]*title="([^"]*)"', seg)
            title = unescape(tm.group(1)) if tm else ""
            results.append(Anime(bangumi_id=bangumi_id, title=title))
        return results

    # ---------- 检测更新（RSS） ----------

    def _resolve_subgroup_id(self, anime: Anime, subgroup: str) -> str | None:
        """按字幕组名从详情页解析 subgroupid，找到返回 ID，找不到返回 None。"""
        resp = self.session.get(
            f"{self.base_url}/Home/Bangumi/{anime.bangumi_id}",
            timeout=self.timeout,
        )
        resp.raise_for_status()
        html = resp.text
        # 详情页每个字幕组一块：<div class="subgroup-text" id="{id}">...<a ...>名字</a>
        for m in re.finditer(r'<div class="subgroup-text" id="(\d+)">.*?</div>', html, re.S):
            seg = m.group(0)
            nm = re.search(r'<a href="/Home/PublishGroup/\d+"[^>]*>(.*?)</a>', seg)
            if not nm:
                continue
            name = unescape(nm.group(1))
            if subgroup in name or name in subgroup:
                return m.group(1)
        print("该字幕组没有对应番剧资源或不存在该字幕组")
        print("以下是其他字幕源")    
        return None

    def get_updates(self, anime: Anime, subgroup: str | None = None) -> list[Episode]:
        params = {"bangumiId": anime.bangumi_id}
        # 指定字幕组：先解析名字→ID，原生 RSS 过滤（更省流量更准）
        if subgroup:
            sid = self._resolve_subgroup_id(anime, subgroup)
            if sid:
                params["subgroupid"] = sid
        resp = self.session.get(
            f"{self.base_url}/RSS/Bangumi",
            params=params,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        text = resp.text

        episodes: list[Episode] = []
        for item in ET.fromstring(text).iter("item"):
            title_el = item.find("title")
            link_el = item.find("link")
            title = title_el.text if title_el is not None else ""
            link = link_el.text if link_el is not None else ""
            # pubDate 在 <torrent> 命名空间里，按本地名逐层找，避免命名空间写死
            pub_date = ""
            torrent_el = next((c for c in item if _localname(c.tag) == "torrent"), None)
            if torrent_el is not None:
                pub_el = next((c for c in torrent_el if _localname(c.tag) == "pubDate"), None)
                pub_date = pub_el.text if pub_el is not None else ""
            episodes.append(Episode(title=title, pub_date=pub_date, page_url=link))
        # 按时间倒序（最新在前）
        episodes.sort(key=lambda e: e.pub_date, reverse=True)
        return episodes

    # ---------- 取磁力 ----------

    def get_magnet(self, episode: Episode) -> str:
        if not episode.page_url:
            return ""
        resp = self.session.get(episode.page_url, timeout=self.timeout)
        resp.raise_for_status()
        html = resp.text
        m = re.search(r"magnet:\?xt=urn:btih:[a-zA-Z0-9]+[^\"\s<>]*", html)
        if not m:
            return ""
        return unescape(m.group(0))
