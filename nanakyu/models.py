"""统一anime格式"""

from dataclasses import dataclass

@dataclass
class Anime:
    bangumi_id: str          # 蜜柑番剧 ID
    title: str               # 番剧标题
    last_update: str = ""    # 上次更新时间（ISO 字符串），空 = 还没查过
    added_at: str = ""       # 加入清单时间

    def to_dict(self) -> dict:
        return {
            "bangumi_id": self.bangumi_id,
            "title": self.title,
            "last_update": self.last_update,
            "added_at": self.added_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Anime":
        return cls(
            bangumi_id=str(data.get("bangumi_id", "")),
            title=data.get("title", ""),
            last_update=data.get("last_update", ""),
            added_at=data.get("added_at", ""),
        )


@dataclass
class Episode:
    title: str             # RSS 条目标题，如"葬送的芙莉莲 第1话 旅途的出发"
    pub_date: str = ""     # 发布日期（ISO 字符串）
    page_url: str = ""     # 单集页地址，取磁力用
    magnet: str = ""       # 磁力链接，取到前为空
