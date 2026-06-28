import re

from typing import List
from selectolax.lexbor import LexborHTMLParser


REGEX_VIDEO_CHECK_URL = re.compile(r'(.*?)xvideos.com/video(.*?)')
REGEX_VIDEO_M3U8 = re.compile(r"html5player\.setVideoHLS\('([^']+)'\);")
REGEX_IFRAME = re.compile(r'video-embed" type="text" readonly value="(.*?)" class="form-control"')

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.xvideos.com/",
    "X-Requested-With": "XMLHttpRequest", # For Account stuff
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

def extractor_account(html: str) -> List[str]:
    video_urls = []
    tree = LexborHTMLParser(html)

    # Target the container div using its distinct classes instead of the duplicate ID
    divs = tree.css("div.frame-block")

    for stuff in divs:
        # Safely find the title paragraph
        title_p = stuff.css_first("p.title")
        if title_p:
            a_tag = title_p.css_first("a")
            if a_tag:
                video_url = a_tag.attributes.get("href")
                if video_url:
                    video_urls.append(f"https://www.xvideos.com{video_url}")

    return video_urls


def is_next_page(html_content: str, current_page: int | None = None):
    """
    This function will check if another page is available so that the iterator in base_api can continue.
    """

    tree = LexborHTMLParser(html_content)







