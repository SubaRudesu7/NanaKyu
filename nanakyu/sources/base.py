from abc import ABC, abstractmethod

from ..data.models import Anime, Episode

"""统一数据源接口。换源不换接口：新源实现这三个方法即可替换。"""


class DataSource(ABC):

    @abstractmethod
    def search(self, keyword: str) -> list[Anime]:
        """按关键词搜索番剧，返回候选列表。"""

    @abstractmethod
    def get_updates(self, anime: Anime, subgroup: str | None = None) -> list[Episode]:
        """检测一部番的更新，返回新集列表（按时间倒序）。"""

    @abstractmethod
    def get_magnet(self, episode: Episode) -> str:
        """取一集的磁力链接，找不到返回空串。"""
