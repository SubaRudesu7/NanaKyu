import json
import os
import re
from datetime import datetime
from html import unescape
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from .models import Anime, Episode
from .source import DataSource

BASE_URL = "https://mikanani.kas.pub"

load_dotenv()  # 从项目根 .env 加载 MIKAN_USER / MIKAN_PASS


class MyBangumiSource(DataSource):
    """基于蜜柑 MyBangumi 订阅的数据源：账号登录 → 拉订阅 → 展开取磁力。"""

    def __init__(self, username: str | None = None, password: str | None = None,
                 cookie_file: str = "data/mikan_cookies.txt",
                 base_url: str = BASE_URL, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self.cookie_file = cookie_file
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})
        # 未显式传账号密码时，从环境变量读取
        username = username or os.environ.get("MIKAN_USER", "")
        password = password or os.environ.get("MIKAN_PASS", "")
        if not (username and password):
            raise RuntimeError("缺少蜜柑账号密码：请传 username/password 或设置 MIKAN_USER/MIKAN_PASS")
        if not self._load_cookie():
            self._login(username, password)

    # ---------- 登录 / cookie ----------

    def _load_cookie(self) -> bool:
        try:
            with open(self.cookie_file, encoding="utf-8") as f:
                jar = requests.utils.cookiejar_from_dict(json.load(f))
            self.session.cookies.update(jar)
            # 试探一次：MyBangumi 是否仍为登录态
            r = self.session.get(f"{self.base_url}/Home/MyBangumi", timeout=self.timeout)
            return r.status_code == 200 and "data-bangumiid" in r.text
        except Exception:
            return False

    def _save_cookie(self) -> None:
        Path(self.cookie_file).parent.mkdir(parents=True, exist_ok=True)
        with open(self.cookie_file, "w", encoding="utf-8") as f:
            json.dump(requests.utils.dict_from_cookiejar(self.session.cookies), f)

    def _login(self, username: str, password: str) -> None:
        # GET 登录页拿 __RequestVerificationToken（ASP.NET 双绑定：cookie+表单）
        r = self.session.get(f"{self.base_url}/Account/Login", timeout=self.timeout)
        token = BeautifulSoup(r.text, "html.parser").find(
            "input", {"name": "__RequestVerificationToken"})["value"]
        r = self.session.post(
            f"{self.base_url}/Account/Login",
            data={"UserName": username, "Password": password,
                  "RememberMe": "false",
                  "__RequestVerificationToken": token},
            timeout=self.timeout, allow_redirects=False)
        if r.status_code != 302:
            raise RuntimeError("蜜柑登录失败：账号或密码错误")
        self._save_cookie()

    # ---------- 订阅列表 ----------

    def list_subscriptions(self) -> list[Anime]:
        r = self.session.get(f"{self.base_url}/Home/MyBangumi", timeout=self.timeout)
        soup = BeautifulSoup(r.text, "html.parser")
        animes = []
        for block in soup.select(".sk-bangumi .an-ul li"):
            span = block.select_one("[data-bangumiid]")
            title = block.select_one(".an-text")
            if span and title:
                animes.append(Anime(
                    bangumi_id=span["data-bangumiid"],
                    title=unescape(title.get("title", "")),
                ))
        return animes

    # ---------- 取该番订阅组的条目（含磁力） ----------

    def get_updates(self, anime: Anime, subgroup: str | None = None) -> list[Episode]:
        r = self.session.get(
            f"{self.base_url}/Home/ExpandBangumi",
            params={"bangumiId": anime.bangumi_id, "showSubscribed": "true"},
            timeout=self.timeout)
        soup = BeautifulSoup(r.text, "html.parser")
        episodes = []
        # 只取第一字幕组块（subgroup-0）的条目 = 订阅组
        first = soup.select_one("div.js-expand_bangumi-subgroup-0-episodes")
        if not first:
            return []
        for li in first.select("li"):
            name_a = li.select_one("a.magnet-link-wrap")
            magnet_a = li.select_one("a[data-clipboard-text^='magnet:']")
            date_div = li.select_one(".res-date")
            if not (name_a and magnet_a):
                continue
            episodes.append(Episode(
                title=name_a.get_text(" ", strip=True),
                pub_date=self._norm_date(date_div.get_text(strip=True)) if date_div else "",
                magnet=unescape(magnet_a["data-clipboard-text"]),
            ))
        episodes.sort(key=lambda e: e.pub_date, reverse=True)
        return episodes

    @staticmethod
    def _norm_date(s: str) -> str:
        """'2026/08/07' → '2026-08-07'（统一成可比较格式）。"""
        return s.replace("/", "-")

    def get_magnet(self, episode: Episode) -> str:
        return episode.magnet  # ExpandBangumi 已自带磁力，无需再请求

    def search(self, keyword: str) -> list[Anime]:
        """订阅模式不走关键词搜索，返回空。"""
        return []
