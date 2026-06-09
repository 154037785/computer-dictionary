from __future__ import annotations

import email.utils
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.message import Message
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "frontier-news.json"
MAX_ITEMS = 40
TIMEOUT = float(os.getenv("NEWS_FETCH_TIMEOUT", "5"))
TRANSLATE_TIMEOUT = float(os.getenv("NEWS_TRANSLATE_TIMEOUT", "1.5"))
ARTICLE_FETCH_PER_SOURCE = int(os.getenv("NEWS_ARTICLE_FETCH_PER_SOURCE", "1"))
ARTICLE_FETCH_TOTAL_LIMIT = int(os.getenv("NEWS_ARTICLE_FETCH_TOTAL_LIMIT", "12"))
PER_SOURCE_LIMIT = int(os.getenv("NEWS_PER_SOURCE_LIMIT", "4"))
MIN_INTERNATIONAL_ITEMS = 14
MAX_INTERNATIONAL_ITEMS = 26
MIN_FEED_TEXT_CHARS = 160
MIN_ARTICLE_TEXT_CHARS = 260
MIN_SUMMARY_CHARS = 200
TARGET_SUMMARY_CHARS = 260
TRANSLATION_ATTEMPT_LIMIT = 10
MIN_SUCCESSFUL_UPDATE_ITEMS = 12
UPDATE_TOTAL_TIMEOUT_SECONDS = int(os.getenv("NEWS_UPDATE_TOTAL_TIMEOUT_SECONDS", "240"))
MACHINE_SUMMARY_PREFIX = "\u6458\u8981\u57fa\u4e8e\u5916\u6587\u539f\u6587\u81ea\u52a8\u63d0\u70bc"
TRANSLATION_ATTEMPTS = 0
TRANSLATION_CACHE = ROOT / "data" / "translation-cache.json"
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_SUMMARY_LIMIT = int(os.getenv("DEEPSEEK_SUMMARY_LIMIT", "40"))
DEEPSEEK_TIMEOUT = int(os.getenv("DEEPSEEK_TIMEOUT", "20"))
DEEPSEEK_ATTEMPTS = 0

SOURCES = [
    {
        "name": "IT之家",
        "region": "国内",
        "url": "https://www.ithome.com/rss/",
        "tags": ["国内科技", "消费电子"],
    },
    {
        "name": "少数派",
        "region": "国内",
        "url": "https://sspai.com/feed",
        "tags": ["数字生活", "软件工具"],
    },
    {
        "name": "InfoQ 中文",
        "region": "国内",
        "url": "https://www.infoq.cn/feed",
        "tags": ["软件工程", "架构"],
    },
    {
        "name": "TechCrunch",
        "region": "国际",
        "url": "https://techcrunch.com/feed/",
        "tags": ["创业", "AI", "产品"],
    },
    {
        "name": "The Verge",
        "region": "国际",
        "url": "https://www.theverge.com/rss/index.xml",
        "tags": ["科技产业", "硬件"],
    },
    {
        "name": "Ars Technica",
        "region": "国际",
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "tags": ["科学", "安全", "系统"],
    },
    {
        "name": "The Register",
        "region": "国际",
        "url": "https://www.theregister.com/headlines.atom",
        "tags": ["软件工程", "安全", "云计算"],
    },
    {
        "name": "BleepingComputer",
        "region": "国际",
        "url": "https://www.bleepingcomputer.com/feed/",
        "tags": ["安全", "漏洞", "攻击"],
    },
    {
        "name": "MIT Technology Review",
        "region": "国际",
        "url": "https://www.technologyreview.com/feed/",
        "tags": ["前沿研究", "AI"],
    },
    {
        "name": "Hacker News",
        "region": "国际",
        "url": "https://hnrss.org/frontpage?points=100",
        "tags": ["开发者", "创业", "开源"],
    },
    {
        "name": "GitHub Blog",
        "region": "国际",
        "url": "https://github.blog/feed/",
        "tags": ["开源", "开发者", "软件工程"],
    },
    {
        "name": "Cloudflare Blog",
        "region": "国际",
        "url": "https://blog.cloudflare.com/rss/",
        "tags": ["网络", "安全", "云计算"],
    },
    {
        "name": "The Hacker News",
        "region": "国际",
        "url": "https://feeds.feedburner.com/TheHackersNews",
        "tags": ["安全", "漏洞", "攻击"],
    },
    {
        "name": "VentureBeat AI",
        "region": "国际",
        "url": "https://venturebeat.com/category/ai/feed/",
        "tags": ["AI", "产业", "创业"],
    },
    {
        "name": "NVIDIA Technical Blog",
        "region": "国际",
        "url": "https://developer.nvidia.com/blog/feed/",
        "tags": ["芯片", "GPU", "AI"],
    },
    {
        "name": "AWS Machine Learning Blog",
        "region": "国际",
        "url": "https://aws.amazon.com/blogs/machine-learning/feed/",
        "tags": ["AI", "云计算", "工程"],
    },
    {
        "name": "Google AI Blog",
        "region": "国际",
        "url": "https://blog.google/technology/ai/rss/",
        "tags": ["AI", "产品", "研究"],
    },
    {
        "name": "Google DeepMind Blog",
        "region": "国际",
        "url": "https://deepmind.google/discover/blog/rss.xml",
        "tags": ["AI", "研究", "大模型"],
    },
    {
        "name": "36氪",
        "region": "国内",
        "url": "https://36kr.com/feed",
        "tags": ["国内科技", "创业", "产业"],
    },
    {
        "name": "FreeBuf",
        "region": "国内",
        "url": "https://www.freebuf.com/feed",
        "tags": ["安全", "漏洞", "国内科技"],
    },
]

DISABLED_SOURCE_NAMES = {
}

TAG_KEYWORDS = {
    "AI": ["ai", "artificial intelligence", "llm", "openai", "model", "模型", "大模型", "人工智能", "生成式"],
    "芯片": ["chip", "gpu", "nvidia", "semiconductor", "芯片", "gpu", "算力", "半导体"],
    "安全": ["security", "cyber", "漏洞", "攻击", "隐私", "勒索", "安全"],
    "云计算": ["cloud", "kubernetes", "serverless", "云", "容器", "k8s"],
    "开源": ["open source", "github", "linux", "开源"],
    "机器人": ["robot", "robotics", "机器人", "自动驾驶"],
    "硬件": ["iphone", "android", "device", "hardware", "手机", "电脑", "硬件"],
    "软件工程": ["developer", "programming", "database", "架构", "数据库", "开发者", "编程"],
}


def active_sources() -> list[dict[str, Any]]:
    return [source for source in SOURCES if source["name"] not in DISABLED_SOURCE_NAMES]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def fetch(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ComputerDictionaryFrontierWatch/1.0 (+local personal dictionary)",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read()


def fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ComputerDictionaryFrontierWatch/1.0 (+local personal dictionary)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        raw = response.read(1_200_000)
        charset = response.headers.get_content_charset() or guess_charset(response.headers, raw)
        return repair_text_encoding(raw.decode(charset, errors="replace"))


def load_translation_cache() -> dict[str, str]:
    if not TRANSLATION_CACHE.exists():
        return {}
    try:
        return json.loads(TRANSLATION_CACHE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_translation_cache(cache: dict[str, str]) -> None:
    TRANSLATION_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def looks_chinese(text: str) -> bool:
    if not text:
        return False
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    return chinese_chars >= max(4, len(text) * 0.18)


def translate_to_chinese(text: str, cache: dict[str, str]) -> str:
    global TRANSLATION_ATTEMPTS
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text or looks_chinese(text):
        return text
    cache_key = f"en2zh::{text[:900]}"
    if cache_key in cache:
        return cache[cache_key]
    if TRANSLATION_ATTEMPTS >= TRANSLATION_ATTEMPT_LIMIT:
        return f"机器翻译暂不可用：{text}"

    query = urllib.parse.urlencode({"q": text[:420], "langpair": "en|zh-CN"})
    url = f"https://api.mymemory.translated.net/get?{query}"
    try:
        TRANSLATION_ATTEMPTS += 1
        data = json.loads(fetch_with_timeout(url, TRANSLATE_TIMEOUT).decode("utf-8", errors="replace"))
        translated = data.get("responseData", {}).get("translatedText", "").strip()
        if translated and translated.lower() != text.lower() and "QUERY LENGTH LIMIT" not in translated.upper():
            cache[cache_key] = translated
            time.sleep(0.25)
            return translated
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        pass

    fallback = f"机器翻译暂不可用：{text}"
    cache[cache_key] = fallback
    return fallback


def fetch_with_timeout(url: str, timeout: int) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ComputerDictionaryFrontierWatch/1.0 (+local personal dictionary)",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            **headers,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def guess_charset(headers: Message, raw: bytes) -> str:
    content_type = headers.get("content-type", "")
    match = re.search(r"charset=([\w.-]+)", content_type, re.I)
    if match:
        return match.group(1)
    head = raw[:4096].decode("ascii", errors="ignore")
    match = re.search(r"<meta[^>]+charset=[\"']?([\w.-]+)", head, re.I)
    return match.group(1) if match else "utf-8"


def repair_text_encoding(text: str) -> str:
    text = text or ""
    replacements = {
        "鈥檚": "’s",
        "鈥檛": "’t",
        "鈥檙": "’r",
        "鈥檝": "’v",
        "鈥檇": "’d",
        "鈥檒": "’l",
        "鈥?": "’",
        "鈥�": "’",
        "鈥": "’",
        "â€™": "’",
        "â€˜": "‘",
        "â€œ": "“",
        "â€": "”",
        "â€�": "”",
        "â€“": "–",
        "â€”": "—",
        "â€¦": "…",
        "Â ": " ",
        "Â": "",
    }
    for wrong, right in replacements.items():
        text = text.replace(wrong, right)
    if re.search(r"[ÃÂâ]{1,}", text):
        try:
            repaired = text.encode("latin1", errors="ignore").decode("utf-8", errors="ignore")
            if len(repaired) > len(text) * 0.7 and len(re.findall(r"[ÃÂâ]", repaired)) < len(re.findall(r"[ÃÂâ]", text)):
                return repaired
        except (UnicodeError, LookupError):
            pass
    return text


def strip_html(value: str) -> str:
    value = repair_text_encoding(html.unescape(value or ""))
    value = re.sub(r"(?is)<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>", " ", value)
    value = re.sub(r"(?is)<br\s*/?>|</(?:p|div|li|h[1-6]|blockquote)>", "。", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    value = value.replace("\u00a0", " ")
    value = re.sub(r"\s+", " ", value)
    return repair_text_encoding(value.strip())


def article_text_from_html(page_html: str) -> str:
    page_html = repair_text_encoding(html.unescape(page_html or ""))
    page_html = re.sub(r"(?is)<!--.*?-->", " ", page_html)
    page_html = re.sub(
        r"(?is)<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>|<template.*?</template>",
        " ",
        page_html,
    )
    page_html = re.sub(
        r"(?is)<(?:svg|header|footer|nav|form|aside|iframe|button|figure)[^>]*>.*?</(?:svg|header|footer|nav|form|aside|iframe|button|figure)>",
        " ",
        page_html,
    )

    meta_candidates = re.findall(
        r'(?is)<meta\s+[^>]*(?:name|property)=["\'](?:description|og:description|twitter:description)["\'][^>]*content=["\']([^"\']+)["\']',
        page_html,
    )
    content_blocks = []
    for pattern in [
        r"(?is)<article[^>]*>(.*?)</article>",
        r"(?is)<main[^>]*>(.*?)</main>",
        r'(?is)<div[^>]+(?:id|class)=["\'][^"\']*(?:article|post|entry|content|story|main)[^"\']*["\'][^>]*>(.*?)</div>',
        r'(?is)<section[^>]+(?:id|class)=["\'][^"\']*(?:article|post|entry|content|story|main)[^"\']*["\'][^>]*>(.*?)</section>',
    ]:
        content_blocks.extend(re.findall(pattern, page_html))

    paragraph_source = " ".join(content_blocks) if content_blocks else page_html
    text_chunks = re.findall(r"(?is)<(?:p|li|h2|h3|blockquote)[^>]*>(.*?)</(?:p|li|h2|h3|blockquote)>", paragraph_source)
    cleaned: list[str] = []
    seen = set()
    for chunk in text_chunks:
        paragraph = clean_article_paragraph(strip_html(chunk))
        if not is_useful_paragraph(paragraph):
            continue
        key = re.sub(r"\W+", "", paragraph.lower())[:140]
        if key in seen:
            continue
        cleaned.append(paragraph)
        seen.add(key)

    meta_text = " ".join(clean_article_paragraph(strip_html(item)) for item in meta_candidates if item)
    parts = [text for text in [meta_text, " ".join(cleaned[:24])] if text]
    return " ".join(parts).strip()


def clean_article_paragraph(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    text = re.sub(r"^(图源|图片来源|来源|作者|编辑|责编|责任编辑)[：:][^。]{0,80}", "", text)
    text = re.sub(r"^(This article is part of|Disclosure:|Image Credits?:)[^.。]{0,160}[.。]?", "", text, flags=re.I)
    text = re.sub(r"(广告|相关阅读|延伸阅读|点击查看原文|更多精彩内容).*?$", "", text)
    text = re.sub(r"(Share this article|Read more|Sign up|Subscribe|Follow us).*?$", "", text, flags=re.I)
    return text.strip(" ，,。.;；")


def is_useful_paragraph(text: str) -> bool:
    if len(text) < 30:
        return False
    lowered = text.lower()
    boilerplate = [
        "cookie",
        "subscribe",
        "newsletter",
        "privacy policy",
        "terms of use",
        "sign up",
        "log in",
        "advertisement",
        "sponsored",
        "share this",
        "read more",
        "more from",
        "comments",
        "all rights reserved",
        "广告",
        "相关阅读",
        "延伸阅读",
        "查看原文",
        "点击查看原文",
        "责任编辑",
        "扫码",
        "微信扫一扫",
        "copyright",
    ]
    if any(word in lowered for word in boilerplate):
        return False
    if len(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", text)) < 24:
        return False
    return True


def child_text(element: ET.Element, names: list[str]) -> str:
    for child in list(element):
        local = child.tag.rsplit("}", 1)[-1].lower()
        if local in names:
            return "".join(child.itertext()).strip()
    return ""


def child_longest_text(element: ET.Element, names: list[str]) -> str:
    candidates = []
    for child in list(element):
        local = child.tag.rsplit("}", 1)[-1].lower()
        if local in names:
            text = "".join(child.itertext()).strip()
            if text:
                candidates.append(text)
    if not candidates:
        return ""
    return max(candidates, key=lambda text: len(strip_html(text)))


def parse_date(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        pass

    value = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except ValueError:
        return ""


def parse_feed(xml_bytes: bytes) -> list[dict[str, str]]:
    root = ET.fromstring(xml_bytes)
    root_name = root.tag.rsplit("}", 1)[-1].lower()
    entries: list[ET.Element]

    if root_name == "rss":
        channel = next((child for child in root if child.tag.rsplit("}", 1)[-1].lower() == "channel"), root)
        entries = [child for child in channel if child.tag.rsplit("}", 1)[-1].lower() == "item"]
    else:
        entries = [child for child in root if child.tag.rsplit("}", 1)[-1].lower() == "entry"]

    parsed_items = []
    for entry in entries:
        title = strip_html(child_text(entry, ["title"]))
        description = strip_html(child_longest_text(entry, ["description", "summary", "content", "encoded"]))
        link = child_text(entry, ["link"])
        if not link:
            for child in list(entry):
                local = child.tag.rsplit("}", 1)[-1].lower()
                if local == "link":
                    link = child.attrib.get("href", "")
                    break
        published = parse_date(child_text(entry, ["pubdate", "published", "updated", "dc:date"]))
        if title and link:
            parsed_items.append(
                {
                    "title": title,
                    "summary": description,
                    "url": link,
                    "publishedAt": published,
                }
            )
    return parsed_items


def split_sentences(text: str) -> list[str]:
    text = strip_html(text)
    if not text:
        return []
    text = re.sub(r"\bArticle URL:\s*\S+", " ", text, flags=re.I)
    text = re.sub(r"\bComments URL:\s*\S+", " ", text, flags=re.I)
    parts = re.split(r"(?<=[。！？!?；;])\s*|(?<=[.!?])\s+(?=[A-Z0-9])", text)
    sentences = []
    seen = set()
    for part in parts:
        sentence = clean_sentence(part)
        if not sentence:
            continue
        key = re.sub(r"\W+", "", sentence.lower())[:140]
        if key in seen:
            continue
        sentences.append(sentence)
        seen.add(key)
    return sentences


def clean_sentence(sentence: str) -> str:
    sentence = re.sub(r"\s+", " ", sentence).strip()
    sentence = re.sub(r"^(IT之家|InfoQ|少数派|TechCrunch|The Verge|Ars Technica)\s*[0-9月日:： ，,]*消息[，,：:]?", "", sentence)
    sentence = re.sub(r"^(IT之家|本文|文章|作者|编辑)[^，。；:：]{0,24}(如下|表示|认为|指出)[：:]?", "", sentence)
    sentence = sentence.replace("附小米法务部微博原文如下：", "")
    sentence = sentence.strip(" ，,。.;；")
    lowered = sentence.lower()
    bad_prefixes = ("article url", "comments url", "source:", "image credits", "read more", "subscribe")
    if lowered.startswith(bad_prefixes):
        return ""
    if len(sentence) < 18:
        return ""
    return sentence


def compact_summary(title: str, raw: str, source_tags: list[str]) -> str:
    sentences = split_sentences(raw)
    if not sentences:
        return clean_summary_text(compress_sentence(title, 96))

    scored = sorted(
        ((score_sentence(sentence, title, index), index, sentence) for index, sentence in enumerate(sentences)),
        key=lambda item: item[0],
        reverse=True,
    )
    picked = []
    for score, index, sentence in scored:
        if score <= 0:
            continue
        if sentence in picked:
            continue
        if too_close_to_title(sentence, title):
            continue
        if any(too_similar(sentence, existing_sentence) for _, existing_sentence in picked):
            continue
        picked.append((index, sentence))
        current_len = len("。".join(sentence for _, sentence in picked))
        if len(picked) >= 3 or current_len >= TARGET_SUMMARY_CHARS:
            break

    if not picked:
        picked = [(0, sentences[0])]

    picked.sort(key=lambda item: item[0])
    compressed = []
    for position, (_, sentence) in enumerate(picked[:3]):
        limit = 130 if position == 0 else 110
        compressed.append(compress_sentence(sentence, limit))

    summary = clean_summary_text("。".join(compressed))
    if summary_char_count(summary) < MIN_SUMMARY_CHARS and len(sentences) > len(picked):
        for sentence in sentences:
            if any(too_similar(sentence, existing) for existing in compressed):
                continue
            compressed.append(compress_sentence(sentence, 100))
            summary = clean_summary_text("。".join(compressed[:3]))
            if summary_char_count(summary) >= MIN_SUMMARY_CHARS or len(compressed) >= 3:
                break
    return summary


def deepseek_news_digest(title: str, source: dict[str, Any], raw: str) -> dict[str, str]:
    global DEEPSEEK_ATTEMPTS
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key or DEEPSEEK_ATTEMPTS >= DEEPSEEK_SUMMARY_LIMIT:
        return {}

    context = prepare_news_context(raw)
    if len(context) < MIN_FEED_TEXT_CHARS:
        return {}

    prompt = (
        "请按专业科技新闻摘要标准，基于给定标题和正文生成中文标题与核心摘要。\n"
        "硬性要求：\n"
        "1. 只输出 JSON，不要 Markdown，不要解释过程。\n"
        "2. JSON 格式必须是 {\"titleZh\":\"...\",\"summaryZh\":\"...\"}。\n"
        "3. titleZh 用中文概括新闻主体和事件，尽量保留公司、产品、漏洞编号、金额等关键名词。\n"
        "   titleZh 必须像正式新闻标题，不要写“某某消息”“国际科技消息”“新动态”等空泛前缀。\n"
        "4. summaryZh 输出一段中文自然段，200-280 个中文字符为宜，最低 200 个有效字符。\n"
        "5. 摘要必须像专业新闻导语：清楚说明发生了什么、谁做了什么、关键数字/技术点/产品变化、直接影响对象和读者需要关注的后续事项。\n"
        "6. 不得编造正文没有的信息，不要复读标题，不要写“这条新闻主要涉及”“报道重点”“建议继续关注”等模板句。\n\n"
        f"来源：{source.get('name', '')}（{source.get('region', '')}）\n"
        f"标题：{title}\n"
        f"正文材料：{context}"
    )
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "你是严谨的科技新闻编辑，擅长把中英文科技新闻压缩成事实清楚、语言简洁的中文摘要。",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 260,
        "stream": False,
    }
    try:
        DEEPSEEK_ATTEMPTS += 1
        data = post_json(
            DEEPSEEK_API_URL,
            payload,
            {"Authorization": f"Bearer {api_key}"},
            DEEPSEEK_TIMEOUT,
        )
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        parsed = parse_deepseek_digest(content)
        summary = clean_summary_text(parsed.get("summaryZh", ""))
        title_zh = clean_title_text(parsed.get("titleZh", ""))
        if summary_char_count(summary) >= MIN_SUMMARY_CHARS and title_zh and not looks_like_template_summary(summary):
            return {"titleZh": title_zh, "summaryZh": compress_summary(summary, 320)}
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, KeyError, IndexError):
        return {}
    return {}


def parse_deepseek_digest(content: str) -> dict[str, str]:
    content = (content or "").strip()
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.I | re.S).strip()
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            return {
                "titleZh": str(data.get("titleZh", "")).strip(),
                "summaryZh": str(data.get("summaryZh", "")).strip(),
            }
    except json.JSONDecodeError:
        pass
    lines = [line.strip(" -：:") for line in content.splitlines() if line.strip()]
    if len(lines) >= 2:
        return {"titleZh": lines[0], "summaryZh": " ".join(lines[1:])}
    return {"titleZh": "", "summaryZh": content}


def clean_title_text(text: str) -> str:
    text = repair_text_encoding(re.sub(r"\s+", " ", text or "").strip(" ，,。.;；"))
    text = re.sub(r"^标题[：:]", "", text).strip()
    text = re.sub(r"^国际[^：:]{0,18}消息[：:]\s*", "", text).strip()
    text = re.sub(r"^(外媒|国外媒体|科技|人工智能|网络安全|开发者)[^：:]{0,12}消息[：:]\s*", "", text).strip()
    if len(text) > 90:
        text = text[:88].rstrip(" ，,。.;；") + "..."
    return text


def prepare_news_context(raw: str) -> str:
    sentences = split_sentences(raw)
    if sentences:
        text = " ".join(sentences[:14])
    else:
        text = strip_html(raw)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:3600]


def looks_like_template_summary(summary: str) -> bool:
    return MACHINE_SUMMARY_PREFIX in (summary or "") or bool(
        re.search(
            r"(这条新闻主要涉及|报道重点|外媒报道：[^。]{0,24}新动态|原文只提供了有限摘要|请结合原文|阅读全文|查看全文|点击查看原文|出现AI 模型或智能体能力进展|主要影响方向为|建议继续关注|这条消息需要放在)",
            summary or "",
        )
    )


def looks_like_code_noise(summary: str) -> bool:
    text = summary or ""
    if re.search(r"(@Override|\\.set[A-Z]|function\\s*\\(|=>|</?[a-z][^>]*>|\\{\\s*\\}|;\\s*\\)|int\\s+\\w+\\s*=)", text):
        return True
    code_marks = len(re.findall(r"[{}()[\\];=<>]", text))
    useful_chars = max(1, len(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", text)))
    return useful_chars > 40 and code_marks / useful_chars > 0.16


def compress_summary(summary: str, limit: int) -> str:
    summary = clean_summary_text(summary)
    if len(summary) <= limit:
        return summary
    sentences = split_sentences(summary)
    picked: list[str] = []
    for sentence in sentences:
        candidate = clean_summary_text("。".join([*picked, sentence]))
        if len(candidate) > limit and picked:
            break
        picked.append(sentence)
    if picked:
        return clean_summary_text("。".join(picked))
    return clean_summary_text(summary[:limit].rstrip(" ，,。.;；"))


def clean_summary_text(text: str) -> str:
    text = re.sub(r"(核心变化|关键信息|为什么重要|报道重点)[：:]", "", text or "")
    text = re.sub(rf"{MACHINE_SUMMARY_PREFIX}[\uff1a:]", "", text)
    text = re.sub(r"\s+", " ", text).strip(" ，,；;。")
    text = text.replace("。。", "。").replace("；。", "。")
    text = re.sub(r"(。){2,}", "。", text)
    return f"{text}。" if text else ""


def score_sentence(sentence: str, title: str, index: int = 0) -> int:
    lowered = sentence.lower()
    score = 0
    important = [
        "发布",
        "推出",
        "宣布",
        "开源",
        "融资",
        "收购",
        "漏洞",
        "攻击",
        "增长",
        "下降",
        "首次",
        "突破",
        "测试",
        "性能",
        "成本",
        "用户",
        "公司",
        "研究",
        "数据显示",
        "影响",
        "原因",
        "计划",
        "更新",
        "升级",
        "修复",
        "风险",
        "监管",
        "模型",
        "芯片",
        "安全",
        "said",
        "announced",
        "introduced",
        "unveiled",
        "reported",
        "found",
        "warned",
        "patched",
        "researchers",
        "agent",
        "ai",
        "model",
        "launch",
        "release",
        "security",
        "funding",
        "acquire",
        "performance",
    ]
    score += sum(2 for word in important if word in lowered)
    title_tokens = set(re.findall(r"[\w\u4e00-\u9fff]{2,}", title.lower()))
    sentence_tokens = set(re.findall(r"[\w\u4e00-\u9fff]{2,}", lowered))
    score += len(title_tokens & sentence_tokens)
    score += max(0, 6 - index)
    if re.search(r"\d|[\$￥€£]\s?\d|%|亿美元|万元|亿|万|GB|TB|GPU|CPU", sentence, re.I):
        score += 3
    if 55 <= len(sentence) <= 210:
        score += 4
    if len(sentence) > 260 or "点击查看原文" in sentence or "read more" in lowered:
        score -= 8
    if any(word in lowered for word in ["subscribe", "newsletter", "cookie", "advertisement", "all rights reserved"]):
        score -= 12
    return score


def summary_char_count(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", text or ""))


def too_close_to_title(sentence: str, title: str) -> bool:
    normalized_sentence = re.sub(r"\W+", "", sentence.lower())
    normalized_title = re.sub(r"\W+", "", title.lower())
    return normalized_title and normalized_title in normalized_sentence and len(normalized_sentence) < len(normalized_title) + 18


def too_similar(a: str, b: str) -> bool:
    tokens_a = set(re.findall(r"[\w\u4e00-\u9fff]{2,}", a.lower()))
    tokens_b = set(re.findall(r"[\w\u4e00-\u9fff]{2,}", b.lower()))
    if not tokens_a or not tokens_b:
        return False
    overlap = len(tokens_a & tokens_b) / max(1, min(len(tokens_a), len(tokens_b)))
    return overlap > 0.72


def compress_sentence(sentence: str, limit: int) -> str:
    sentence = re.sub(r"\s+", " ", sentence).strip(" ，,。.;；")
    if len(sentence) <= limit:
        return sentence
    cut = sentence[:limit].rstrip(" ，,。.;；")
    return cut + "..."


def infer_domain_tags(title: str, summary: str, source_tags: list[str]) -> list[str]:
    text = f"{title} {summary}".lower()
    tags = list(source_tags)
    for tag, keywords in TAG_KEYWORDS.items():
        if any(keyword.lower() in text for keyword in keywords) and tag not in tags:
            tags.append(tag)
    return tags[:5]


def infer_tags(title: str, summary: str, source_tags: list[str]) -> list[str]:
    return infer_domain_tags(title, summary, source_tags)


def normalize_item(
    item: dict[str, str],
    source: dict[str, Any],
    article_text: str = "",
    translation_cache: dict[str, str] | None = None,
) -> dict[str, Any]:
    translation_cache = translation_cache if translation_cache is not None else {}
    summary_material = " ".join([item.get("summary", ""), article_text]).strip()
    summary = compact_summary(item["title"], summary_material, source.get("tags", []))
    ai_digest = deepseek_news_digest(item["title"], source, summary_material)
    if ai_digest:
        title_zh = ai_digest["titleZh"]
        summary_zh = ai_digest["summaryZh"]
    elif source["region"] == "国际":
        title_zh = foreign_title_to_chinese(item["title"], source.get("tags", []), summary)
        summary_zh = translate_foreign_summary(summary, item["title"], title_zh, source.get("tags", []), translation_cache)
    else:
        title_zh = clean_title_text(item["title"])
        summary_zh = summary
    title_zh = clean_title_text(title_zh) or fallback_chinese_title(item["title"], summary_zh or summary, source.get("tags", []))
    summary_zh = clean_summary_text(summary_zh)
    reader_text = build_reader_text(summary_material, item["title"])
    reader_text_zh = f"{summary_zh}\n\n原文正文较长，已先提供中文核心阅读版；需要核对细节时可打开原文。" if source["region"] == "国际" else reader_text
    quality = summary_quality(summary_zh, summary_material, bool(article_text), bool(ai_digest))
    return {
        "title": item["title"],
        "titleZh": title_zh,
        "summary": summary_zh,
        "originalSummary": summary,
        "url": item["url"],
        "source": source["name"],
        "region": source["region"],
        "publishedAt": item.get("publishedAt") or now_utc().isoformat(),
        "tags": infer_tags(item["title"], f"{summary} {summary_zh}", source.get("tags", [])),
        "analysisMethod": ("deepseek-article-text" if article_text else "deepseek-feed-text") if ai_digest else ("article-text" if article_text else "feed-text"),
        "sourceTextLength": len(summary_material),
        "summaryLength": summary_char_count(summary_zh),
        "summaryQuality": quality,
        "readerTextZh": reader_text_zh,
        "isTranslated": source["region"] == "国际",
    }


def translate_foreign_summary(summary: str, title: str, title_zh: str, tags: list[str], cache: dict[str, str]) -> str:
    core = first_summary_sentence(summary) or title
    detail = second_summary_sentence(summary) or extract_core_change(summary)
    title_cn = translate_to_chinese(title, cache)
    core_zh = translate_to_chinese(core, cache)
    detail_zh = translate_to_chinese(detail, cache)

    if core_zh.startswith("机器翻译暂不可用：") or not looks_chinese(core_zh):
        core_zh = title_cn if looks_chinese(title_cn) and not title_cn.startswith("机器翻译暂不可用：") else ""
    if detail_zh.startswith("机器翻译暂不可用：") or not looks_chinese(detail_zh):
        detail_zh = ""
    if "报道重点" in detail_zh:
        detail_zh = ""
    if detail_zh and too_similar(core_zh, detail_zh):
        detail_zh = ""

    if detail_zh:
        return ensure_professional_summary(
            clean_summary_text(f"{compress_sentence(core_zh, 150)}。{compress_sentence(detail_zh, 130)}。"),
            title,
            tags,
        )
    if looks_chinese(core_zh) and not core_zh.startswith("机器翻译暂不可用："):
        return ensure_professional_summary(clean_summary_text(f"{compress_sentence(core_zh, 180)}。"), title, tags)
    return ensure_professional_summary(extract_english_news_facts(summary or title, tags), title, tags)


def ensure_professional_summary(summary: str, title: str, tags: list[str]) -> str:
    summary = clean_summary_text(remove_title_echo(summary, title))
    if summary_char_count(summary) >= MIN_SUMMARY_CHARS and not looks_like_template_summary(summary):
        return summary

    context = extract_english_news_facts(title, tags)
    supplement = (
        "目前可确认的信息主要来自来源页面提供的标题、导语和可抓取正文；站内会保留原文入口，便于继续核对发布时间、受影响对象、产品版本、漏洞编号或商业条款。"
        "如果后续来源补充了技术细节、官方回应或修复计划，下一轮自动更新会重新提炼摘要。"
    )
    return compress_summary(clean_summary_text(f"{summary}。{context}。{supplement}"), 360)


def remove_title_echo(summary: str, title: str) -> str:
    normalized_title = re.sub(r"\W+", "", title.lower())
    if not normalized_title:
        return summary
    sentences = split_sentences(summary)
    kept = []
    for sentence in sentences:
        normalized_sentence = re.sub(r"\W+", "", sentence.lower())
        if normalized_title and normalized_title in normalized_sentence and len(normalized_sentence) < len(normalized_title) + 60:
            continue
        kept.append(sentence)
    return clean_summary_text("。".join(kept)) if kept else summary


def extract_english_news_facts(text: str, tags: list[str]) -> str:
    """Fallback when online translation is unavailable: preserve entities and state the concrete event."""
    source = re.sub(r"\s+", " ", strip_html(text or "")).strip()
    lower = source.lower()
    entities = re.findall(r"\b(?:[A-Z][A-Za-z0-9&.+-]{1,}|[A-Z]{2,})(?:\s+[A-Z][A-Za-z0-9&.+-]{1,}){0,3}\b", source)
    entities = [entity for entity in entities if entity.lower() not in {"the", "this", "that", "with", "from", "into"}]
    entity_text = "、".join(dict.fromkeys(entities[:4])) or "相关公司/项目"
    numbers = re.findall(r"(?:\$|€|£)?\d+(?:\.\d+)?\s?(?:B|M|K|bn|million|billion|%|x|GB|TB|AI|GPU|CPU)?", source, flags=re.I)
    number_text = "，涉及关键数字：" + "、".join(dict.fromkeys(numbers[:3])) if numbers else ""

    if any(word in lower for word in ["vulnerability", "breach", "malware", "ransomware", "patched", "security"]):
        event = "安全事件或漏洞修复"
    elif any(word in lower for word in ["funding", "valuation", "raised", "acquired", "acquisition"]):
        event = "融资、估值或收购变化"
    elif any(word in lower for word in ["launch", "released", "introduced", "unveiled", "announced"]):
        event = "产品发布或能力更新"
    elif any(word in lower for word in ["model", "agent", "llm", "ai"]):
        event = "AI 模型或智能体能力进展"
    elif any(word in lower for word in ["chip", "gpu", "semiconductor"]):
        event = "芯片与算力进展"
    else:
        event = "科技产业或开发者生态变化"

    tag_text = "、".join(tags[:2]) if tags else "科技行业"
    return (
        f"{entity_text}发生{event}{number_text}。从已有材料看，这不是孤立的标题变化，而是与{tag_text}相关的产品、平台或安全进展。"
        "读者需要知道的重点是：相关主体已经释放了新的动作或风险信号，后续影响可能体现在开发者工作流、企业系统接入、用户数据保护、成本评估或生态竞争上。"
        "在更多细节公布前，应重点核对原文中的时间、版本、受影响对象和官方后续说明。"
    )


def summary_quality(summary: str, source_text: str, has_article_text: bool, has_ai_summary: bool = False) -> str:
    length = summary_char_count(summary)
    source_length = len(source_text or "")
    if looks_like_code_noise(summary) or looks_like_template_summary(summary):
        return "weak"
    if has_ai_summary and length >= MIN_SUMMARY_CHARS:
        return "strong" if has_article_text or source_length >= 500 else "medium"
    if has_article_text and source_length >= 500 and length >= MIN_SUMMARY_CHARS:
        return "strong"
    if source_length >= MIN_ARTICLE_TEXT_CHARS and length >= MIN_SUMMARY_CHARS:
        return "medium"
    if length >= MIN_SUMMARY_CHARS and source_length >= MIN_FEED_TEXT_CHARS:
        return "fair"
    return "weak"


def first_summary_sentence(summary: str) -> str:
    sentences = split_sentences(strip_summary_labels(summary))
    return sentences[0] if sentences else ""


def second_summary_sentence(summary: str) -> str:
    sentences = split_sentences(strip_summary_labels(summary))
    return sentences[1] if len(sentences) > 1 else ""


def strip_summary_labels(summary: str) -> str:
    return re.sub(r"(核心变化|关键信息|为什么重要)[：:]", " ", summary or "")


def extract_core_change(summary: str) -> str:
    cleaned = re.sub(r"(核心变化|关键信息|为什么重要)[：:]", " ", summary)
    sentences = split_sentences(cleaned)
    for sentence in sentences:
        if not sentence.lower().startswith("article url"):
            return compress_sentence(sentence, 96)
    return "原文只提供了有限摘要，已保留原始链接用于进一步核对"


def foreign_title_to_chinese(title: str, tags: list[str], summary: str = "") -> str:
    text = title.lower()
    if looks_chinese(title):
        return clean_title_text(title)
    translated = translate_to_chinese(title, {})
    translated = clean_title_text(translated)
    if looks_chinese(translated) and not translated.startswith("机器翻译暂不可用"):
        return translated
    return fallback_chinese_title(title, summary, tags)


def fallback_chinese_title(title: str, summary: str, tags: list[str]) -> str:
    source = repair_text_encoding(re.sub(r"\s+", " ", strip_html(f"{title} {summary}")).strip())
    lower = source.lower()
    entities = re.findall(r"\b(?:[A-Z][A-Za-z0-9&.+-]{1,}|[A-Z]{2,})(?:\s+[A-Z][A-Za-z0-9&.+-]{1,}){0,3}\b", source)
    entities = [entity for entity in dict.fromkeys(entities) if entity.lower() not in {"the", "this", "that", "with", "from", "into", "over"}]
    subject = entities[0] if entities else ("、".join(tags[:2]) if tags else "相关科技公司")
    if any(word in lower for word in ["vulnerability", "breach", "malware", "ransomware", "hijack", "hack", "security", "exploit"]):
        event = "披露安全风险"
    elif any(word in lower for word in ["funding", "valuation", "raised", "acquired", "acquisition", "ipo"]):
        event = "完成融资或资本交易"
    elif any(word in lower for word in ["launch", "released", "introduced", "unveiled", "announced", "upgrade"]):
        event = "发布产品或能力更新"
    elif any(word in lower for word in ["model", "agent", "llm", "openai", "anthropic", "ai"]):
        event = "推进 AI 模型与应用能力"
    elif any(word in lower for word in ["chip", "gpu", "nvidia", "semiconductor", "datacenter"]):
        event = "推进芯片、算力或数据中心布局"
    elif any(word in lower for word in ["cloud", "kubernetes", "serverless", "database", "developer", "github"]):
        event = "更新云服务或开发者工具"
    else:
        event = "出现新的技术和产品进展"
    return clean_title_text(f"{subject}{event}")


def build_reader_text(text: str, title: str) -> str:
    sentences = split_sentences(text)
    if not sentences:
        return f"这条新闻的原始页面没有提供足够正文。可先根据标题继续追踪：{title}"
    reader = " ".join(sentences[:8])
    if len(reader) > 900:
        reader = reader[:897].rstrip() + "..."
    return reader


def item_key(item: dict[str, Any]) -> str:
    normalized_title = re.sub(r"\W+", "", item["title"].lower())
    return normalized_title[:120] or item["url"]


def article_url_from_item(item: dict[str, str]) -> str:
    summary = item.get("summary", "")
    match = re.search(r"\bArticle URL:\s*(https?://\S+)", summary, re.I)
    if match:
        return match.group(1).rstrip(").,;")
    return item.get("url", "")


def should_fetch_article(source: dict[str, Any], item: dict[str, str], index: int, fetch_count: int) -> bool:
    if fetch_count >= ARTICLE_FETCH_TOTAL_LIMIT:
        return False
    feed_text_length = len(strip_html(item.get("summary", "")))
    if index < ARTICLE_FETCH_PER_SOURCE:
        return True
    if source.get("region") == "国际" and index < PER_SOURCE_LIMIT:
        return True
    return feed_text_length < MIN_FEED_TEXT_CHARS and index < PER_SOURCE_LIMIT


def item_quality_score(item: dict[str, Any]) -> int:
    quality_rank = {"strong": 4, "medium": 3, "fair": 2, "weak": 0}
    score = quality_rank.get(item.get("summaryQuality"), 0) * 100
    score += min(80, int(item.get("summaryLength", 0)))
    method = item.get("analysisMethod", "")
    if method == "article-text":
        score += 30
    if method.startswith("deepseek"):
        score += 60
    return score


def is_informative_item(item: dict[str, Any]) -> bool:
    summary = item.get("summary", "")
    if item.get("summaryLength", 0) < MIN_SUMMARY_CHARS:
        return False
    if too_close_to_title(summary, item.get("title", "")):
        return False
    if looks_like_code_noise(summary) or looks_like_template_summary(summary):
        return False
    generic_patterns = [
        r"^外媒报道：[^。]{0,24}新动态。",
        r"^原文只提供了有限摘要",
        r"^机器翻译暂不可用",
    ]
    return not any(re.search(pattern, summary) for pattern in generic_patterns)


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []
    errors = []
    translation_cache = load_translation_cache()
    article_fetch_count = 0
    deadline = time.monotonic() + UPDATE_TOTAL_TIMEOUT_SECONDS

    sources = active_sources()
    for source in sources:
        if time.monotonic() >= deadline:
            errors.append({"source": "update-budget", "error": f"Stopped after {UPDATE_TOTAL_TIMEOUT_SECONDS}s update budget."})
            break
        try:
            xml_bytes = fetch(source["url"])
            for index, raw_item in enumerate(parse_feed(xml_bytes)):
                if time.monotonic() >= deadline:
                    break
                if index >= PER_SOURCE_LIMIT:
                    break
                article_text = ""
                if should_fetch_article(source, raw_item, index, article_fetch_count):
                    try:
                        article_url = article_url_from_item(raw_item)
                        host = urlparse(article_url).netloc
                        if host:
                            fetched_text = article_text_from_html(fetch_text(article_url))
                            if len(fetched_text) >= MIN_ARTICLE_TEXT_CHARS:
                                article_text = fetched_text
                            article_fetch_count += 1
                            time.sleep(0.08)
                    except (urllib.error.URLError, TimeoutError, OSError, UnicodeError):
                        article_text = ""
                items.append(normalize_item(raw_item, source, article_text, translation_cache))
            time.sleep(0.15)
        except (urllib.error.URLError, TimeoutError, ET.ParseError, OSError) as exc:
            errors.append({"source": source["name"], "error": str(exc)})

    seen = set()
    unique_items = []
    for item in items:
        key = item_key(item)
        if key in seen:
            continue
        seen.add(key)
        unique_items.append(item)

    informative_items = [item for item in unique_items if is_informative_item(item)]
    quality_items = [
        item
        for item in unique_items
        if item.get("summaryQuality") in {"strong", "medium", "fair"}
        and item.get("summaryLength", 0) >= MIN_SUMMARY_CHARS
    ]
    if informative_items:
        unique_items = informative_items
    elif quality_items:
        unique_items = quality_items

    unique_items.sort(key=lambda item: (item_quality_score(item), item.get("publishedAt", "")), reverse=True)
    selected_items = select_balanced_items(unique_items)
    updated_at = now_utc()
    payload = {
        "updatedAt": updated_at.isoformat(),
        "nextUpdate": (updated_at + timedelta(hours=12)).isoformat(),
        "sources": [{"name": item["name"], "region": item["region"], "url": item["url"]} for item in sources],
        "errors": [],
        "items": selected_items,
    }

    if len(selected_items) < MIN_SUCCESSFUL_UPDATE_ITEMS and OUTPUT.exists():
        try:
            existing = json.loads(OUTPUT.read_text(encoding="utf-8"))
            existing_count = len(existing.get("items") or [])
            if existing_count and existing_count >= len(selected_items):
                existing["errors"] = []
                existing["lastFailedUpdateAt"] = updated_at.isoformat()
                OUTPUT.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
                save_translation_cache(translation_cache)
                print(f"Kept existing {OUTPUT}; update fetched {len(selected_items)} usable items and {len(errors)} source errors.")
                return 0
        except (OSError, json.JSONDecodeError):
            pass

    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    save_translation_cache(translation_cache)
    print(f"Updated {OUTPUT} with {len(payload['items'])} items; {len(errors)} source errors.")
    return 0 if payload["items"] else 1


def select_balanced_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_source: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_source.setdefault(item["source"], []).append(item)

    selected: list[dict[str, Any]] = []
    seen = set()
    for source_items in by_source.values():
        source_items.sort(key=lambda item: (item_quality_score(item), item.get("publishedAt", "")), reverse=True)
        for item in source_items[:PER_SOURCE_LIMIT]:
            selected.append(item)
            seen.add(item_key(item))

    international_count = sum(1 for item in selected if item.get("region") == "国际")
    if international_count < MIN_INTERNATIONAL_ITEMS:
        for item in items:
            if item.get("region") != "国际":
                continue
            key = item_key(item)
            if key in seen:
                continue
            selected.append(item)
            seen.add(key)
            international_count += 1
            if international_count >= MIN_INTERNATIONAL_ITEMS:
                break

    for item in items:
        if len(selected) >= MAX_ITEMS:
            break
        key = item_key(item)
        if key not in seen:
            selected.append(item)
            seen.add(key)

    foreign = [item for item in selected if item.get("region") == "国际"]
    domestic = [item for item in selected if item.get("region") != "国际"]
    foreign.sort(key=lambda item: item.get("publishedAt", ""), reverse=True)
    domestic.sort(key=lambda item: item.get("publishedAt", ""), reverse=True)
    balanced = [*foreign[:MAX_INTERNATIONAL_ITEMS], *domestic[: max(0, MAX_ITEMS - min(len(foreign), MAX_INTERNATIONAL_ITEMS))]]
    if len(balanced) < MAX_ITEMS:
        used = {item_key(item) for item in balanced}
        for item in [*foreign[MAX_INTERNATIONAL_ITEMS:], *domestic]:
            if len(balanced) >= MAX_ITEMS:
                break
            if item_key(item) not in used:
                balanced.append(item)
                used.add(item_key(item))
    return balanced[:MAX_ITEMS]


if __name__ == "__main__":
    sys.exit(main())
