from ..core.checker import Checker
from ..data.models import Anime
from ..data.storage import Storage
from ..sources.base import DataSource
from ..sources.mybangumi import MyBangumiSource


class NanaKyuApp:
    """统一门面：把登录 / 存储 / 查更新封装成几个简单方法。"""

    def __init__(self, storage_path: str = "data/tracking.json"):
        self.source = MyBangumiSource()
        self.storage = Storage(storage_path)

    def list_subscriptions(self) -> list[Anime]:
        """列出蜜柑账号订阅的番。"""
        return self.source.list_subscriptions()

    def check(self) -> list[dict]:
        return Checker(self.source, self.storage).check()
