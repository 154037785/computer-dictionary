from __future__ import annotations

import json
import sys
import time
import urllib.error
import xml.etree.ElementTree as ET
from datetime import timedelta
from pathlib import Path
from typing import Any

from update_frontier_news import (
    OUTPUT as FRONTIER_OUTPUT,
    article_text_from_html,
    fetch,
    fetch_text,
    is_informative_item,
    item_key,
    normalize_item,
    now_utc,
    parse_feed,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "wechat-news.json"
MAX_ITEMS = 48
PER_SOURCE_LIMIT = 8
ARTICLE_FETCH_PER_SOURCE = 1
ARTICLE_FETCH_TOTAL_LIMIT = 16

# WeChat public accounts do not expose an official RSS API. These candidate
# routes are best-effort RSSHub/aggregation routes; failures are recorded and
# the script falls back to Chinese technical long-form sources.
WECHAT_CANDIDATE_SOURCES = [
    {
        "name": "InfoQ 中文公众号候选源",
        "region": "公众号",
        "url": "https://rsshub.app/wechat/ershicimi/infoqchina",
        "tags": ["公众号", "架构", "软件工程"],
    },
    {
        "name": "机器之心公众号候选源",
        "region": "公众号",
        "url": "https://rsshub.app/wechat/ershicimi/jiqizhixin",
        "tags": ["公众号", "AI", "机器学习"],
    },
    {
        "name": "量子位公众号候选源",
        "region": "公众号",
        "url": "https://rsshub.app/wechat/ershicimi/QbitAI",
        "tags": ["公众号", "AI", "产业"],
    },
]

FALLBACK_LONGFORM_SOURCES = [
    {
        "name": "InfoQ 中文深度",
        "region": "公众号/中文深度",
        "url": "https://www.infoq.cn/feed",
        "tags": ["架构", "软件工程", "中文深度"],
    },
    {
        "name": "少数派深度",
        "region": "公众号/中文深度",
        "url": "https://sspai.com/feed",
        "tags": ["工具", "数字生活", "中文深度"],
    },
    {
        "name": "美团技术团队",
        "region": "公众号/技术团队",
        "url": "https://tech.meituan.com/feed/",
        "tags": ["后端", "工程", "技术团队"],
    },
    {
        "name": "阮一峰网络日志",
        "region": "公众号/中文深度",
        "url": "https://www.ruanyifeng.com/blog/atom.xml",
        "tags": ["前端", "开发者", "中文深度"],
    },
    {
        "name": "机器之心",
        "region": "公众号/中文深度",
        "url": "https://www.jiqizhixin.com/rss",
        "tags": ["AI", "机器学习", "中文深度"],
    },
    {
        "name": "腾讯云开发者",
        "region": "公众号/技术团队",
        "url": "https://cloud.tencent.com/developer/rss",
        "tags": ["云计算", "开发者", "技术团队"],
    },
    {
        "name": "阿里云开发者",
        "region": "公众号/技术团队",
        "url": "https://developer.aliyun.com/rss",
        "tags": ["云计算", "开发者", "技术团队"],
    },
    {
        "name": "掘金技术社区",
        "region": "公众号/中文深度",
        "url": "https://juejin.cn/rss",
        "tags": ["前端", "后端", "开发者"],
    },
    {
        "name": "博客园技术文章",
        "region": "公众号/中文深度",
        "url": "https://www.cnblogs.com/rss",
        "tags": ["开发者", "后端", "中文深度"],
    },
    {
        "name": "开源中国资讯",
        "region": "公众号/中文深度",
        "url": "https://www.oschina.net/news/rss",
        "tags": ["开源", "开发者", "中文深度"],
    },
    {
        "name": "SegmentFault 思否",
        "region": "公众号/中文深度",
        "url": "https://segmentfault.com/feeds",
        "tags": ["开发者", "前端", "后端"],
    },
]


def collect_from_source(source: dict[str, Any], errors: list[dict[str, str]], article_budget: list[int]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    try:
        raw_feed = fetch(source["url"])
        for index, raw_item in enumerate(parse_feed(raw_feed)):
            article_text = ""
            if index < ARTICLE_FETCH_PER_SOURCE and article_budget[0] > 0:
                try:
                    article_text = article_text_from_html(fetch_text(raw_item["url"]))
                    article_budget[0] -= 1
                    time.sleep(0.2)
                except (urllib.error.URLError, TimeoutError, OSError, UnicodeError):
                    article_text = ""
            item = normalize_item(raw_item, source, article_text, {})
            item["region"] = source["region"]
            item["isTranslated"] = False
            items.append(item)
        time.sleep(0.4)
    except (urllib.error.URLError, TimeoutError, ET.ParseError, OSError) as exc:
        errors.append({"source": source["name"], "error": str(exc)})
    return items


def select_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_source: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_source.setdefault(item["source"], []).append(item)

    selected: list[dict[str, Any]] = []
    seen = set()
    for source_items in by_source.values():
        source_items.sort(key=lambda item: item.get("publishedAt", ""), reverse=True)
        for item in source_items[:PER_SOURCE_LIMIT]:
            key = item_key(item)
            if key in seen:
                continue
            selected.append(item)
            seen.add(key)

    source_cap = max(PER_SOURCE_LIMIT, (MAX_ITEMS // max(1, len(by_source))) + 2)
    source_counts = {source: 0 for source in by_source}
    for item in selected:
        source_counts[item["source"]] = source_counts.get(item["source"], 0) + 1

    for item in sorted(items, key=lambda item: item.get("publishedAt", ""), reverse=True):
        if len(selected) >= MAX_ITEMS:
            break
        if source_counts.get(item["source"], 0) >= source_cap:
            continue
        key = item_key(item)
        if key not in seen:
            selected.append(item)
            seen.add(key)
            source_counts[item["source"]] = source_counts.get(item["source"], 0) + 1

    selected.sort(key=lambda item: item.get("publishedAt", ""), reverse=True)
    return selected[:MAX_ITEMS]


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    errors: list[dict[str, str]] = []
    items: list[dict[str, Any]] = []
    article_budget = [ARTICLE_FETCH_TOTAL_LIMIT]

    for source in WECHAT_CANDIDATE_SOURCES:
        items.extend(collect_from_source(source, errors, article_budget))

    if len(items) < 18:
        for source in FALLBACK_LONGFORM_SOURCES:
            items.extend(collect_from_source(source, errors, article_budget))

    quality_items = [
        item
        for item in items
        if is_informative_item(item)
        if item.get("summaryQuality") in {"strong", "medium", "fair"}
        and item.get("summaryLength", 0) >= 50
    ]
    selected = select_items(quality_items if len(quality_items) >= 12 else [item for item in items if item.get("sourceTextLength", 0) >= 80])
    if len(selected) < 12:
        selected = select_items(items)

    updated_at = now_utc()
    payload = {
        "updatedAt": updated_at.isoformat(),
        "nextUpdate": (updated_at + timedelta(hours=12)).isoformat(),
        "sources": [
            {"name": item["name"], "region": item["region"], "url": item["url"]}
            for item in [*WECHAT_CANDIDATE_SOURCES, *FALLBACK_LONGFORM_SOURCES]
        ],
        "errors": errors,
        "items": selected,
        "note": "微信公众号无官方 RSS；候选公众号源不可用时，使用中文技术团队/深度推文源兜底。",
    }

    if not selected and OUTPUT.exists():
        try:
            existing = json.loads(OUTPUT.read_text(encoding="utf-8"))
            if existing.get("items"):
                existing["errors"] = errors
                existing["lastFailedUpdateAt"] = updated_at.isoformat()
                OUTPUT.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"Kept existing {OUTPUT}; update fetched 0 items and {len(errors)} source errors.")
                return 0
        except (OSError, json.JSONDecodeError):
            pass

    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Updated {OUTPUT} with {len(selected)} items; {len(errors)} source errors.")
    return 0 if selected else 1


if __name__ == "__main__":
    sys.exit(main())
