import re

from selectolax.lexbor import LexborHTMLParser


REGEX_VIDEO_M3U8 = re.compile(r"html5player\.setVideoHLS\('([^']+)'\);")
REGEX_IFRAME = re.compile(r'video-embed" type="text" readonly value="(.*?)" class="form-control"')

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.TARGET_SITE_DOMAIN.com/",  # Match the site you are actually scraping!
    "X-Requested-With": "XMLHttpRequest",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

cookies = None


# Please submit your login cookies here like:

"""
cookies = {
session_token = <token>
session_token_auth = <token>
}
"""


def extractor_account(html: str) -> list[dict[str, str]]:
    videos = []
    tree = LexborHTMLParser(html)

    # Target the main container blocks
    divs = tree.css("div.frame-block")
    for video in divs:
        _video_url = video.css_first("a").attributes.get("href")
        video_url = f"https://www.xvideos.com{_video_url}"

        _img = video.css_first("img")
        thumbnail = _img.attributes.get("src")
        video_id = _img.attributes.get("data-videoid")
        preview_video = _img.attributes.get("data-pvv")

        _meta = video.css_first("div.thumb-under")
        title = _meta.css_first("a").text()
        length_node = _meta.css_first("span.duration")
        length = length_node.text(strip=True) if length_node else None

        other = _meta.css_first("p.metadata")
        views = None
        views_node = other.css_first("span.bg > span:not(.duration) > span")
        if views_node:
            raw_text = views_node.text(strip=True)
            if raw_text.startswith("-"):
                raw_text = raw_text[1:].strip()
                views = raw_text.split()[0] if " " in raw_text else raw_text


        stuff = {
            "title": title,
            "url": video_url,
            "thumbnail_url": thumbnail,
            "video_id": video_id,
            "preview_video_url": preview_video,
            "length": length,
            "views": views
        }

        videos.append(stuff)

    return videos


def is_next_page(html_content: str, current_page: int | None = None):
    """
    This function will check if another page is available so that the iterator in base_api can continue.
    """

    tree = LexborHTMLParser(html_content)







