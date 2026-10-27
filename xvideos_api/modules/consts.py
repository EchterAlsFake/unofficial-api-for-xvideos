import json
import html
from urllib.parse import urljoin, urlsplit, urlunsplit
import re

from selectolax.lexbor import LexborHTMLParser


REGEX_VIDEO_M3U8 = re.compile(r"html5player\.setVideoHLS\('([^']+)'\)")
REGEX_IFRAME = re.compile(r'id=["\']copy-video-embed["\'][^>]*value=["\']([^"\']+)["\']')

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.xvideos.com/",
    "Connection": "keep-alive",
}

cookies = None


# Please submit your login cookies here like:

"""
cookies = {
session_token = <token>
session_token_auth = <token>
}
"""


def extractor_profile_json(content: str, base_url: str = "https://www.xvideos.com") -> list[dict]:
    data = json.loads(content)
    videos = data.get("videos", [])
    if not isinstance(videos, list):
        raise ValueError("Profile listing did not contain a videos array")
    results = []
    for item in videos:
        if not isinstance(item, dict) or not item.get("u"):
            continue
        url = urljoin(base_url, item["u"])
        parsed = urlsplit(url)
        parts = parsed.path.strip("/").split("/")
        # Profile click links are redirects; use their actual video ID, not eid.
        if parts[0] == "prof-video-click":
            if len(parts) < 5:
                continue
            url = urlunsplit(parsed._replace(path="/video." + parts[-2] + "/" + parts[-1], fragment=""))
        raw_title = item.get("tf") or item.get("t")
        title = html.unescape(raw_title) if raw_title else None
        results.append({
            "url": url,
            "video_id": str(item["id"]) if item.get("id") is not None else None,
            "title": title,
            "thumbnail_url": item.get("i"),
            "length": item.get("d"),
            "views": str(item["n"]) if item.get("n") is not None else None,
        })
    return results


def extractor_account(html: str, base_url: str = "https://www.xvideos.com") -> list[dict[str, str]]:
    videos = []
    tree = LexborHTMLParser(html)

    # Target the main container blocks
    divs = tree.css("div.frame-block") or tree.css("div.thumb-block")
    for video in divs:
        classes = video.attributes.get("class", "")
        if "thumb-block-profile" in classes:
            continue

        a_node = video.css_first("a[href]")
        if not a_node:
            continue
        _video_url = a_node.attributes.get("href")
        if not isinstance(_video_url, str) or not _video_url:
            continue
        # Ensure it's actually a video link and not an ad or profile link
        if not (_video_url.startswith("/video.") or "/video" in _video_url):
            for candidate in video.css("a[href]"):
                chref = candidate.attributes.get("href") or ""
                if chref.startswith("/video.") or "/video" in chref:
                    _video_url = chref
                    break
            else:
                continue

        video_url = urljoin(base_url, _video_url)

        _img = video.css_first("img")
        thumbnail = None
        video_id = None
        preview_video = None
        if _img:
            thumbnail = _img.attributes.get("data-src") or _img.attributes.get("src")
            if thumbnail and "lightbox-blank.gif" in thumbnail:
                thumbnail = _img.attributes.get("data-src") or None
            video_id = _img.attributes.get("data-videoid")
            preview_video = _img.attributes.get("data-pvv")
        if not video_id:
            video_id = video.attributes.get("data-id")

        _meta = video.css_first("div.thumb-under")
        title_node = (_meta.css_first("p.title a") or _meta.css_first("a")) if _meta else None
        title = None
        if title_node:
            title = title_node.attributes.get("title")
            if not title:
                for bad in title_node.css(".duration, .video-hd-mark"):
                    bad.decompose()
                title = title_node.text(strip=True)

        length_node = _meta.css_first("span.duration") if _meta else None
        length = length_node.text(strip=True) if length_node else None

        other = _meta.css_first("p.metadata") if _meta else None
        views = None
        if other:
            views_node = other.css_first("span.bg > span:not(.duration) > span")
            if views_node:
                raw_text = views_node.text()
                raw_text = re.sub(r"^[^\d]*", "", raw_text.strip())
                views = raw_text.split()[0] if raw_text else None

        stuff = {
            "title": title,
            "url": video_url,
            "thumbnail_url": thumbnail,
            "video_id": video_id,
            "preview_video_url": preview_video,
            "length": length,
            "views": views,
        }

        videos.append(stuff)

    return videos


def is_next_page(html_content: str, current_page: int | None = None) -> bool:
    """
    Check if another page is available in the pagination bar.
    """
    tree = LexborHTMLParser(html_content)
    next_node = tree.css_first(".pagination a.next-page, .pagination li.next a, a.next-page")
    return next_node is not None






