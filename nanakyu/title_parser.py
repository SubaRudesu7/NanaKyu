import re


def parse_subgroup(title: str) -> str:
    """从标题开头提取字幕组名（[...] 或 【...】），取不到返回空串。"""
    m = re.match(r"\s*[\[【]\s*([^\]】\d][^\]】]*)", title)
    return m.group(1).strip() if m else ""


def parse_episode(title: str) -> int | None:
    """从标题解析集数，按优先级匹配常见格式。"""
    patterns = [
        r"第\s*(\d+)\s*话",          # 第01话
        r"(?:-|—|\-)\s*(\d+)\b",     # - 09 / — 27（连字符后接数字）
        r"\[(\d+)v?\d*\]",           # [28] / [28v2]
        r"\[(\d+)\s*-\s*(\d+)\]",    # [01-28] 区间，取最后一个
        r"第\s*(\d+)\s*集",          # 第01集
        r"EP?\s*[\.\s]?\s*(\d+)",    # EP.01 / EP01 / EP 01
    ]
    for i, pat in enumerate(patterns):
        m = re.search(pat, title)
        if not m:
            continue
        num = m.group(2 if i == 3 else 1)
        try:
            return int(num)
        except ValueError:
            continue
    return None
