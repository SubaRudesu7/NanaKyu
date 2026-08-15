"""cli.py — 命令行入口。

用法：
    python cli.py subs      列出蜜柑订阅番
    python cli.py check     检测所有订阅更新，输出新集磁力
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from nanakyu import NanaKyuApp


def cmd_subs(app: NanaKyuApp) -> None:
    subs = app.list_subscriptions()
    if not subs:
        print("无订阅")
        return
    for a in subs:
        print(f"{a.bangumi_id}  {a.title}")


def cmd_check(app: NanaKyuApp) -> None:
    results = app.check()
    if not results:
        print("没有新集")
        return
    for r in results:
        print(f"[{r['anime'].title}] {r['episode'].title}")
        print(f"  磁力: {r['magnet']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="NanaKyu 番剧更新检测")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("subs", help="列出订阅番")
    sub.add_parser("check", help="检测订阅更新")

    args = parser.parse_args()
    app = NanaKyuApp()

    if args.command == "subs":
        cmd_subs(app)
    elif args.command == "check":
        cmd_check(app)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
