"""
Copyright (C) 2024-2025 Johannes Habel

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import os
import re
import math
import json
import html
import logging
import asyncio
import argparse
from typing import AsyncGenerator
from dataclasses import dataclass
from functools import cached_property
from selectolax.lexbor import LexborHTMLParser
from curl_cffi.requests import Response, AsyncSession
from base_api.modules.type_hints import DownloadReport
from base_api.modules.static_functions import str_to_bool
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from base_api import ScrapeResult, Helper, BaseCore, on_error_hint, setup_logger, DownloadConfigHLS
from base_api.modules.errors import InvalidProxy, BotProtectionDetected, UnknownError, NetworkRequestError, ResourceGone

from xvideos_api.modules.errors import (NotFound, NetworkError, UnknownNetworkError, BotDetection,
                                        ProxyError, InvalidUrl, InvalidPornstar, DownloadFailed, NoLoginCookies,
                                        )
from xvideos_api.modules.consts import (cookies, headers, extractor_account, REGEX_VIDEO_M3U8, REGEX_IFRAME,
                                        REGEX_VIDEO_CHECK_URL)
from xvideos_api.modules.sorting import Sort, SortVideoTime, SortQuality, SortDate


async def on_error(url: str, error: Exception, attempt: int) -> bool:
    print(f"URL: {url}, ERROR: {error}, Attempt: {attempt}")

    if isinstance(error, ResourceGone):
        return False

    return True


async def get_html_content(core: BaseCore, url: str) -> str | None | dict:
    # What should I do here?
    try:
        content = await core.fetch(url)
        if isinstance(content, str):
            return content

        if isinstance(content, Response):
            if content.status_code == 404:
                raise NotFound(f"Server returned 404 for: {url}")

    except NetworkRequestError as e:
        raise NetworkError(str(e)) from e

    except InvalidProxy as e:
        raise ProxyError(str(e)) from e

    except BotProtectionDetected as e:
        raise BotDetection(str(e)) from e

    except UnknownError as e:
        raise UnknownNetworkError(str(e)) from e


class Account(Helper):
    def __init__(self, core: BaseCore, cookies: dict | None = cookies):
        super().__init__(core=core, video_constructor=VideoBuilder)
        self.core = core
        self.cookies = cookies

        if not self.cookies:
            raise NoLoginCookies("""
You have not provided any login cookies. Please set them in the consts module like:

consts.cookies = {
session_token = <token>
session_token_auth = <token>
            }            
            """)

        assert isinstance(self.core.session, AsyncSession)
        self.core.session.cookies.update(cookies)
        self.core.session.headers.update(headers)
        self.logger = setup_logger(name="XVIDEOS API - [Account]", log_file=None, level=logging.ERROR)


    async def get_recommended_videos(self, pages: int = 2, videos_concurrency: int | None = None,
                                     pages_concurrency: int | None = None,
                                     on_video_error: on_error_hint = on_error,
                                     on_page_error: on_error_hint = None,
                                     keep_original_order: bool = False
                                     ) -> AsyncGenerator[ScrapeResult, None]:

        page_urls = [f"https://www.xvideos.com/history/{page}" for page in range(pages)]
        videos_concurrency = videos_concurrency or self.core.configuration.videos_concurrency
        pages_concurrency = pages_concurrency or self.core.configuration.pages_concurrency
        assert videos_concurrency and pages_concurrency

        async for video in self.iterator(target_page_urls=page_urls, video_link_extractor=extractor_account,
                                         max_video_concurrency=videos_concurrency,
                                         max_page_concurrency=pages_concurrency,
                                         page_request_method="POST",
                                         on_video_error=on_video_error,
                                         on_page_error=on_page_error,
                                         keep_original_order=keep_original_order):

            yield video

    async def get_liked_videos(self, pages: int = 2, videos_concurrency: int | None = None,
                                     pages_concurrency: int | None = None,
                               on_video_error: on_error_hint = on_error,
                               on_page_error: on_error_hint = None,
                               keep_original_order: bool = False
                               ) -> AsyncGenerator[ScrapeResult, None]:

        page_urls = [f"https://www.xvideos.com/videos-i-like/{page}" for page in range(pages)]
        videos_concurrency = videos_concurrency or self.core.configuration.videos_concurrency
        pages_concurrency = pages_concurrency or self.core.configuration.pages_concurrency
        assert videos_concurrency and pages_concurrency
        async for video in self.iterator(target_page_urls=page_urls, video_link_extractor=extractor_account,
                                         max_video_concurrency=videos_concurrency,
                                         max_page_concurrency=pages_concurrency,
                                         page_request_method="POST",
                                         on_video_error=on_video_error,
                                         on_page_error=on_page_error,
                                         keep_original_order=keep_original_order):

            yield video
    async def get_watch_later_videos(self, pages: int = 2, videos_concurrency: int | None = None,
                                     pages_concurrency: int | None = None,
                                     on_video_error: on_error_hint = on_error,
                                     on_page_error: on_error_hint = None,
                                     keep_original_order: bool = False
                                     ) -> AsyncGenerator[ScrapeResult, None]:

        page_urls = [f"https://www.xvideos.com/watch-later/{page}" for page in range(pages)]
        videos_concurrency = videos_concurrency or self.core.configuration.videos_concurrency
        pages_concurrency = pages_concurrency or self.core.configuration.pages_concurrency
        assert videos_concurrency and pages_concurrency
        async for video in self.iterator(target_page_urls=page_urls, video_link_extractor=extractor_account,
                                         max_video_concurrency=videos_concurrency,
                                         max_page_concurrency=pages_concurrency,
                                         page_request_method="POST",
                                         on_video_error=on_video_error,
                                         on_page_error=on_page_error,
                                         keep_original_order=keep_original_order):

            yield video


@dataclass(slots=True)
class VideoMetadata:
    title: str
    description: str
    thumbnail_url: str
    preview_video_url: str
    publish_date: str
    content_url: str
    tags: list
    views: str
    likes: str
    dislikes: str
    rating_votes: str
    comment_count: str
    author: str | None
    length: str
    pornstars: list
    embed_url: str
    cdn_url: str
    m3u8_base_url: str


class Video:
    """
    This class serves as a lightweight class that only holds the necessary attributes and end results.
    If I gave you the full Video class with the HTML, all script tags and so on it would easily
    take up a few megabytes per Video.
    """

    __slots__ = ("metadata", "core")

    def __init__(self, metadata: VideoMetadata, core: BaseCore):
        self.metadata = metadata
        self.core = core

    @property
    def title(self) -> str:
        return self.metadata.title

    @property
    def description(self) -> str:
        return self.metadata.description

    @property
    def thumbnail_url(self) -> str:
        return self.metadata.thumbnail_url

    @property
    def preview_video_url(self) -> str:
        return self.metadata.preview_video_url

    @property
    def publish_date(self) -> str:
        return self.metadata.publish_date

    @property
    def content_url(self) -> str:
        return self.metadata.content_url

    @property
    def tags(self) -> list:
        return self.metadata.tags

    @property
    def views(self) -> str:
        return self.metadata.views

    @property
    def likes(self) -> str:
        return self.metadata.likes

    @property
    def dislikes(self) -> str:
        return self.metadata.dislikes

    @property
    def rating_votes(self) -> str:
        return self.metadata.rating_votes

    @property
    def comment_count(self) -> str:
        return self.metadata.comment_count

    @property
    def length(self) -> str:
        return self.metadata.length

    @property
    def m3u8_base_url(self) -> str:
        return self.metadata.m3u8_base_url

    async def download(self, config: DownloadConfigHLS) -> bool | DownloadReport:
        """
        :param config:
        :return:
        """
        if not config.no_title:
            config.path = os.path.join(config.path, f"{self.title}.mp4")

        config.m3u8_base_url = self.m3u8_base_url

        try:
            return await self.core.download(configuration=config)

        except Exception as e:  # I should improve this in the future
            raise DownloadFailed(str(e))

    @property
    async def author(self) -> Channel | None:
        url = self.metadata.author

        if url:
            channel = Channel(url=url, core=self.core)
            return await channel.init()

        return None

    @property
    async def pornstars(self) -> AsyncGenerator[Pornstar, None]:
        for url in self.metadata.pornstars:
            star = Pornstar(url=url, core=self.core)
            yield await star.init()


class VideoBuilder:
    def __init__(self, url: str, core: BaseCore, html_content: str | None = None):
        """
        :param url: (str) The URL of the video
        """
        self.core = core
        self.url = url
        self.logger = setup_logger(name="XVIDEOS API - [Video]", log_file=None, level=logging.ERROR)
        self.html_content = html_content
        self._lexbor = None
        self.json_data = {}
        self.quality_url_map = None
        self.available_qualities = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.clean()

    def _extract_metadata_sync(self):
        """
        Synchronous method containing all the CPU-heavy HTML parsing work.
        This will be run in a background thread.
        """
        assert self.html_content, str
        self._lexbor = LexborHTMLParser(self.html_content)
        self.json_data = self.meta

        meta = VideoMetadata(
            title=self.title,
            description=self.description,
            thumbnail_url=self.thumbnail_url,
            preview_video_url=self.preview_video_url,
            publish_date=self.publish_date,
            content_url=self.content_url,
            tags=self.tags,
            views=self.views,
            likes=self.likes,
            dislikes=self.dislikes,
            rating_votes=self.rating_votes,
            comment_count=self.comment_count,
            author=self.author,
            length=self.length,
            pornstars=self.pornstars,
            embed_url=self.embed_url,
            cdn_url=self.cdn_url,
            m3u8_base_url=self.m3u8_base_url
        )

        print(f"M3U8 URL: {self.m3u8_base_url}")
        return Video(metadata=meta, core=self.core)

    async def init(self):
        if not self.html_content:
            self.html_content = await get_html_content(core=self.core, url=self.url)

        return await asyncio.to_thread(self._extract_metadata_sync) # Doesn't block the event loop in the iterator

    async def clean(self):
        """
        This function destroys the class without destroying it :)
        """
        self.core = None
        self.url = None
        self.logger = None
        self.html_content = None
        self._lexbor = None
        self.json_data = None
        self.quality_url_map = None
        self.available_qualities = None

    @property
    def lexbor(self) -> LexborHTMLParser:
        if not self._lexbor:
            raise ValueError("You probably forgot to call init")

        return self._lexbor

    @cached_property
    def script_content(self) -> str:
        for node in self.lexbor.css('script'):
            t = node.text()
            if t and "html5player" in t and "setVideoTitle" in t and "setVideoUrlLow" in t:
                return t

        return ""

    @classmethod
    def check_url(cls, url) -> str:
        """
        :param url: (str) The URL of the video
        :return: (str) The URL of the video, if valid, otherwise raises InvalidUrl Exception
        """
        match = REGEX_VIDEO_CHECK_URL.match(url)
        if match:
            return url

        else:
            raise InvalidUrl(f"Invalid Video URL: {url}")

    def _get_json_data(self) -> dict:
        data = {}
        for s in self.lexbor.css('script[type="application/ld+json"]'):
            if not s.text():
                continue
            try:
                data.update(json.loads(s.text()))
            except Exception:
                continue

        return data

    @property
    def meta(self) -> dict:
        j = self._get_json_data()
        # Defensive access because JSON-LD varies
        return {
            "name": j.get("name"),
            "description": j.get("description"),
            "thumbnailUrl": (j.get("thumbnailUrl") or [None])[0] if isinstance(j.get("thumbnailUrl"), list) else j.get(
                "thumbnailUrl"),
            "uploadDate": j.get("uploadDate"),
            "contentUrl": j.get("contentUrl"),
        }

    @cached_property
    def m3u8_base_url(self) -> str:
        return REGEX_VIDEO_M3U8.search(self.script_content).group(1)


    @cached_property
    def title(self) -> str:
        return self.meta["name"] if self.meta["name"] else ""

    @cached_property
    def description(self) -> str:
        return html.unescape(self.json_data["description"])

    @cached_property
    def thumbnail_url(self) -> str:
        return self.json_data["thumbnailUrl"]

    @cached_property
    def preview_video_url(self) -> str:
        thumb = html.unescape(self.json_data["thumbnailUrl"])[0]
        base_url = re.sub(r'/thumbs(169)?(xnxx)?(l*|poster)/', '/videopreview/', thumb[:thumb.rfind("/")])
        suffix = re.search(r'-(\d+)', base_url)
        base_url = re.sub(r'-(\d+)', '', base_url) if suffix else base_url
        return f"{base_url}_169{suffix.group(0) if suffix else ''}.mp4"

    @cached_property
    def publish_date(self) -> str:
        return html.unescape(self.json_data["uploadDate"])

    @cached_property
    def content_url(self) -> str:
        return html.unescape(self.json_data["contentUrl"])

    @cached_property
    def tags(self) -> list:
        elements = self.lexbor.css("a.is-keyword.btn.btn-default")
        return [tag.text() for tag in elements]

    @cached_property
    def views(self) -> str:
        return self.lexbor.css_first("span.icon-f.icf-eye").next.text(strip=True)

    @cached_property
    def likes(self) -> str:
        return self.lexbor.css_first("span.rating-good-nbr").text(strip=True)

    @cached_property
    def dislikes(self) -> str:
        return self.lexbor.css_first("span.rating-bad-nbr").text(strip=True)

    @cached_property
    def rating_votes(self) -> str:
        return self.lexbor.css_first("span.rating-total-txt").text(strip=True)

    @cached_property
    def comment_count(self) -> str:
        return self.lexbor.css_first("button.comments.tab-button").next.next.text(strip=True)

    @cached_property
    def author(self) -> str | None:
        """Returns the Channel object where the video was published on"""
        try:
            link = self.lexbor.css_first("li.main-uploader").css_first('a').attributes.get("href")

        except AttributeError:
            return None

        assert isinstance(link, str)
        if not link.startswith("/profiles"):
            url=f"https://xvideos.com/channels"

        else:
            url=f"https://xvideos.com{link}"

        return url

    @cached_property
    def length(self) -> str:
        return self.lexbor.css_first("span.duration").text(strip=True)

    @cached_property
    def pornstars(self) -> list[str]:
        """
        Returns the Pornstar objects for the Pornstars that are featured in the video
        """
        pornstars = self.lexbor.css('li.model')
        urls = []
        for pornstar in pornstars:
            urls.append(f"https://xvideos.com{pornstar.next.attributes.get('href')}")

        return urls

    @cached_property
    def embed_url(self) -> str:
        assert self.html_content, str
        return REGEX_IFRAME.search(html.unescape(self.html_content)).group(1)

    @cached_property
    def cdn_url(self) -> str:
        return self.json_data["contentUrl"]


class Channel(Helper):
    """
    Returns the Channel object for a Channel. Please note, that the Channel object and the Pornstar object
    are almost identical, but I still differentiated them as two different classes, because TECHNICALLY they are
    different things.

    """
    def __init__(self, url: str, core: BaseCore):
        super().__init__(core=core, video_constructor=VideoBuilder)
        self.core = core
        self.logger = setup_logger(name="XVIDEOS API - [Channel]", log_file=None, level=logging.ERROR)
        if "/channels/" not in url and "profiles" not in url:
            self.logger.warning("/channels/ not in URL. Trying to fix manually. This CAN lead to more errors!")
            self.url = url.replace("xvideos.com/", "xvideos.com/channels/")
        else:
            self.url = url
        self._about_me = None
        self.data = None

    async def init(self):
        base_content = await get_html_content(url=f"{self.url}/videos/best/0", core=self.core)
        about_me_html = await get_html_content(url=f"{self.url}#_tabAboutMe", core=self.core)

        assert isinstance(about_me_html, str)
        assert isinstance(base_content, str)
        self._about_me = LexborHTMLParser(about_me_html)
        self.data = json.loads(base_content)
        return self

    def enable_logging(self, log_file: str | None = None, level: int | None = None, log_ip: str | None = None,
                       log_port: int | None = None):
        if not level:
            level = logging.DEBUG
        self.logger = setup_logger(name="XVIDEOS API - [Channel]", log_file=log_file, level=level, http_ip=log_ip, http_port=log_port)

    @cached_property
    def name(self) -> str:
        return self._about_me.css_first('h2 strong.text-danger').text()

    @cached_property
    def thumbnail_url(self) -> str:
        return self._about_me.css_first('div.profile-pic img').attributes.get('src')

    @cached_property
    def total_videos(self) -> int:
        return int(self.data["nb_videos"])

    @cached_property
    def per_page(self) -> int:
        return int(self.data["nb_per_page"])

    @cached_property
    def total_pages(self) -> int:
        return math.ceil(self.total_videos / self.per_page)

    async def videos(self, pages: int = 0, videos_concurrency: int | None = None, pages_concurrency: int | None = None,
                     on_video_error: on_error_hint = on_error,
                     on_page_error: on_error_hint = None,
                     keep_original_order: bool = False
                     ) -> AsyncGenerator[ScrapeResult, None]:
        if pages > self.total_pages:
            self.logger.warning(f"You want to fetch: {self.total_pages} pages but only: {self.total_pages} are available. Reducing!")
            pages = self.total_pages

        if pages == 0:
            pages = self.total_pages

        page_urls = [f"{self.url}/videos/best/{i}" for i in range(pages)] # Don't exceed total available pages
        self.logger.debug(f"Processing: {len(page_urls)} pages...")
        videos_concurrency = videos_concurrency or self.core.configuration.videos_concurrency
        pages_concurrency = pages_concurrency or self.core.configuration.pages_concurrency
        assert videos_concurrency and pages_concurrency
        async for scrape_result in self.iterator(target_page_urls=page_urls, video_link_extractor=extractor_account,
                                         max_video_concurrency=videos_concurrency,
                                         max_page_concurrency=pages_concurrency, on_page_error=on_page_error,
                                         on_video_error=on_video_error, keep_original_order=keep_original_order):

            yield scrape_result

    @cached_property
    def country(self) -> str:
        return self._about_me.css_first('#pinfo-country span').text(strip=True)

    @cached_property
    def profile_hits(self) -> str:
        return self._about_me.css_first('#pinfo-profile-hits span').text(strip=True)

    @cached_property
    def subscribers(self) -> str:
        return self._about_me.css_first('#pinfo-subscribers span').text(strip=True)

    @cached_property
    def total_video_views(self) -> str:
        return self._about_me.css_first('#pinfo-video-views span').text(strip=True)

    @cached_property
    def signed_up(self) -> str:
        return self._about_me.css_first('#pinfo-signedup span').text(strip=True)

    @cached_property
    def last_activity(self) -> str:
        return self._about_me.css_first('#pinfo-lastactivity span').text(strip=True)

    async def worked_for_with(self):
        names = self._about_me.css('#pinfo-workedfor a')
        links = [a.attributes.get('href') for a in names if a.attributes.get('href')]
        for link in links:
            if not "profile" in link:
                channel = Channel(url=f"https://xvideos.com/channels{link}", core=self.core)
                return await channel.init()

            else:
                channel = Channel(url=f"https://xvideos.com{link}", core=self.core)
                return await channel.init()


class Pornstar(Helper):
    def __init__(self, core: BaseCore, url: str):
        super().__init__(core=core, video_constructor=VideoBuilder)
        self.core = core
        self.url = self.check_url(url)
        self._about_me = None
        self.data = None
        self.logger = setup_logger(name="XVIDEOS API - [Pornstar]", log_file=None, level=logging.ERROR)
        
    async def init(self):
        base_content = await get_html_content(url=f"{self.url}/videos/best/0", core=self.core)
        about_me_html = await get_html_content(url=f"{self.url}#_tabAboutMe", core=self.core)

        assert isinstance(about_me_html, str)
        assert isinstance(base_content, str)
        self._about_me = LexborHTMLParser(about_me_html)
        self.data = json.loads(base_content)
        return self

    def enable_logging(self, log_file: str | None = None, level: int | None = None, log_ip: str | None = None,
                       log_port: int | None = None):
        if not level:
            level = logging.DEBUG
        self.logger = setup_logger(name="XVIDEOS API - [Pornstar]", log_file=log_file, level=level, http_ip=log_ip, http_port=log_port)

    def check_url(self, url):
        if ("/pornstars" not in url) and ("/model" not in url):
            self.logger.error("URL doesn't contain '/pornstars/', seems like a channel URL or is generally invalid!")
            raise InvalidPornstar(
                "It seems like the Pornstar URL is invalid, please note, that channels are NOT supported!")

        return url

    @cached_property
    def name(self) -> str:
        return self._about_me.css_first('h2 strong.text-danger').text()

    @cached_property
    def thumbnail_url(self) -> str:
        return self._about_me.css_first('div.profile-pic img').attributes.get('src')

    @cached_property
    def total_videos(self) -> int:
        return int(self.data["nb_videos"])

    @cached_property
    def per_page(self) -> int:
        return int(self.data["nb_per_page"])

    @cached_property
    def total_pages(self) -> int:
        return math.ceil(self.total_videos / self.per_page)

    async def videos(self, pages: int = 0, videos_concurrency: int | None = None, pages_concurrency: int | None = None,
                     on_video_error: on_error_hint = on_error,
                     on_page_error: on_error_hint = None,
                     keep_original_order: bool = False
                     ) -> AsyncGenerator[ScrapeResult, None]:
        if pages > self.total_pages:
            self.logger.warning(
                f"You want to fetch: {self.total_pages} pages but only: {self.total_pages} are available. Reducing!")
            pages = self.total_pages

        if pages == 0:
            pages = self.total_pages

        page_urls = [f"{self.url}/videos/best/{i}" for i in range(pages)]  # Don't exceed total available pages
        self.logger.debug(f"Processing: {len(page_urls)} pages...")
        videos_concurrency = videos_concurrency or self.core.configuration.videos_concurrency
        pages_concurrency = pages_concurrency or self.core.configuration.pages_concurrency
        assert videos_concurrency and pages_concurrency

        async for scrape_result in self.iterator(target_page_urls=page_urls, video_link_extractor=extractor_account,
                                         max_video_concurrency=videos_concurrency,
                                         max_page_concurrency=pages_concurrency,
                                         on_video_error=on_video_error, keep_original_order=keep_original_order,
                                         on_page_error=on_page_error):

            yield scrape_result


    @cached_property
    def gender(self) -> str:
        return self._about_me.css_first('#pinfo-sex span').text(strip=True)

    @cached_property
    def age(self) -> str:
        """Returns the age of the Pornstar"""
        age = self._about_me.css_first('#pinfo-age span').text(strip=True)
        if int(age) < 18: # lmaooooo
            raise "Wait what????"

        return age

    @cached_property
    def country(self) -> str:
        """Returns the country of the Pornstar"""
        return self._about_me.css_first('#pinfo-country span').text(strip=True)

    @cached_property
    def profile_hits(self) -> str:
        """Returns the current profile hits count (don't know what that is lol)"""
        return self._about_me.css_first('#pinfo-profile-hits span').text(strip=True)

    @cached_property
    def subscriber_count(self) -> str:
        """Returns the current subscriber count of the pornstar"""
        return self._about_me.css_first('#pinfo-subscribers span').text(strip=True)

    @cached_property
    def total_videos_views(self) -> str:
        """Returns the total video views of the pornstar of all videos combined"""
        return self._about_me.css_first('#pinfo-videos-views span').text(strip=True)

    @cached_property
    def sign_up_date(self) -> str:
        """Returns the date where the pornstar signed up his / her account"""
        return self._about_me.css_first('#pinfo-signedup span').text(strip=True)

    @cached_property
    def last_activity(self) -> str:
        """Returns the date of the last activity of the Pornstar"""
        return self._about_me.css_first('#pinfo-lastactivity span').text(strip=True)

    @cached_property
    def video_tags(self) -> str:
        """Returns the video tags the pornstar is often featured in"""
        return self._about_me.css_first('#pinfo-video-tags span').text(strip=True)

    async def worked_for_with(self) -> AsyncGenerator[Channel, None]:
        """
        Returns the channels the pornstar has worked with as a Channel object (Generator)
        """
        names = self._about_me.css('#pinfo-workedfor a')
        links = [a.attributes.get('href') for a in names if a.attributes.get('href')]
        for link in links:
            channel = Channel(core=self.core, url=f"https://www.xvideos.com{link}")
            yield await channel.init()


class Client(Helper):
    def __init__(self, core: BaseCore = BaseCore()):
        super().__init__(core, video_constructor=VideoBuilder)
        self.core = core
        self.core.initialize_session()
        self.logger = setup_logger(name="XVIDEOS API - [Client]", log_file=None, level=logging.ERROR)

    def enable_logging(self, log_file: str | None = None, level: int | None = None, log_ip: str | None = None,
                       log_port: int | None = None):
        if not level:
            level = logging.DEBUG
        self.logger = setup_logger(name="XVIDEOS API - [Client]", log_file=log_file, level=level, http_ip=log_ip, http_port=log_port)

    async def get_video(self, url: str) -> Video:
        """
        :param url: (str) The video URL
        :return: (Video) The video object
        """
        video = VideoBuilder(url, core=self.core)
        return await video.init()

    async def search(self, query: str, sorting_sort: str | Sort = Sort.Sort_relevance,
               sorting_date: str | SortDate = SortDate.Sort_all,
               sorting_time: str | SortVideoTime = SortVideoTime.Sort_all,
               sort_quality: str | SortQuality = SortQuality.Sort_all,
               pages: int | str = "all", videos_concurrency: int | None = None,
               pages_concurrency: int | None = None,
                     on_video_error: on_error_hint = on_error,
                     on_page_error: on_error_hint = None,
                     keep_original_order: bool = False
                     ) -> AsyncGenerator[ScrapeResult, None]:


        query = query.replace(" ", "+")
        p = urlparse(f"https://www.xvideos.com/")
        qs = parse_qs(p.query)
        queries = {
            "k": query,
            "sort": sorting_sort,
            "datef": sorting_date,
            "durf": sorting_time,
            "quality": sort_quality
        }

        for key, value in queries.items():
            if value:
                qs[key] = [str(value)]

        new_query = urlencode(qs, doseq=True)
        url = urlunparse(p._replace(query=new_query))

        page_urls = [] # Empty page urls will lead to automatic iteration

        if isinstance(pages, int):
            page_urls = [f"{url}&p={p}" for p in range(pages)]

        videos_concurrency = videos_concurrency or self.core.configuration.videos_concurrency
        pages_concurrency = pages_concurrency or self.core.configuration.pages_concurrency
        assert videos_concurrency and pages_concurrency
        async for scrape_result in self.iterator(target_page_urls=page_urls, video_link_extractor=extractor_account,
                                         max_video_concurrency=videos_concurrency,
                                         max_page_concurrency=pages_concurrency,
                                         on_video_error=on_video_error, keep_original_order=keep_original_order,
                                         on_page_error=on_page_error,
                                         ):

            yield scrape_result

    async def get_playlist(self, url: str, pages: int = 2, videos_concurrency: int | None = None,
                     pages_concurrency: int | None = None,
                           on_video_error: on_error_hint = on_error,
                           on_page_error: on_error_hint = None,
                           keep_original_order: bool = False
                           ) -> AsyncGenerator[ScrapeResult, None]:
        page_urls = [f"{url}/{page}" for page in range(pages)]
        videos_concurrency = videos_concurrency or self.core.configuration.videos_concurrency
        pages_concurrency = pages_concurrency or self.core.configuration.pages_concurrency
        assert videos_concurrency and pages_concurrency

        async for scrape_result in self.iterator(target_page_urls=page_urls, video_link_extractor=extractor_account,
                                         max_video_concurrency=videos_concurrency,
                                         max_page_concurrency=pages_concurrency,
                                         on_video_error=on_video_error, on_page_error=on_page_error,
                                         keep_original_order=keep_original_order):

            yield scrape_result

    async def get_pornstar(self, url) -> Pornstar:
        pornstar = Pornstar(core=self.core, url=url)
        return await pornstar.init()

    async def get_channel(self, url) -> Channel:
        channel = Channel(url, core=self.core)
        return await channel.init()

    def get_account(self) -> Account:
        account = Account(core=self.core)
        return account


async def run_main():
    parser = argparse.ArgumentParser(description="API Command Line Interface")
    parser.add_argument("--download", metavar="URL (str)", type=str, help="URL to download from")
    parser.add_argument("--quality", metavar="best,half,worst", type=str, help="The video quality (best,half,worst)",
                        required=True)
    parser.add_argument("--file", metavar="Source to .txt file", type=str,
                        help="(Optional) Specify a file with URLs (separated with new lines)")
    parser.add_argument("--output", metavar="Output directory", type=str, help="The output path (with filename)",
                        required=True)
    parser.add_argument("--no-title", metavar="True,False", type=str,
                        help="Whether to apply video title automatically to output path or not", required=True)

    args = parser.parse_args()
    no_title = str_to_bool(args.no_title)

    config = DownloadConfigHLS(
        quality=args.quality,
        path=args.output,
        no_title=no_title
    )

    if args.download:
        client = Client()
        video = await client.get_video(args.download)
        await video.download(config=config)

    if args.file:
        videos = []
        client = Client()

        with open(args.file, "r") as file:
            content = file.read().splitlines()

        for url in content:
            videos.append(await client.get_video(url))

        for video in videos:
            await video.download(quality=args.quality, path=args.output, no_title=no_title)


if __name__ == "__main__":
    asyncio.run(run_main())