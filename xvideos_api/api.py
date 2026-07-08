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
import asyncio
import argparse
import logging
from typing import AsyncGenerator
from dataclasses import dataclass, fields
from selectolax.lexbor import LexborHTMLParser
from curl_cffi.requests import Response, AsyncSession
from base_api.modules.type_hints import DownloadReport
from base_api.modules.static_functions import str_to_bool
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from base_api import ScrapeResult, Helper, BaseCore, on_error_hint, BaseMedia, DownloadConfigHLS
from base_api.modules.errors import InvalidProxy, BotProtectionDetected, UnknownError, NetworkRequestError, ResourceGone

from xvideos_api.modules.errors import (NotFound, NetworkError, UnknownNetworkError, BotDetection,
                                        ProxyError, DownloadFailed, NoLoginCookies)
from xvideos_api.modules.consts import (cookies, headers, extractor_account, REGEX_VIDEO_M3U8, REGEX_IFRAME)
from xvideos_api.modules.sorting import Sort, SortVideoTime, SortQuality, SortDate


logger = logging.getLogger(__name__)


async def on_error(url: str, error: Exception, attempt: int) -> bool:
    logger.error(f"URL: {url}, ERROR: {error}, Attempt: {attempt}")

    if isinstance(error, ResourceGone):
        return False

    return True


async def get_html_content(core: BaseCore, url: str) -> str | None | dict:
    # What should I do here?
    try:
        logger.debug(f"Fetching HTML content for URL: {url}")
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


class Account:
    def __init__(self, core: BaseCore, cookies: dict | None = cookies):
        self.core = core
        self.cookies = cookies
        self.helper = Helper(core=self.core, constructor=Video)

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


    async def get_recommended_videos(self, pages: int = 2, videos_concurrency: int | None = None,
                                     pages_concurrency: int | None = None,
                                     on_video_error: on_error_hint = on_error,
                                     on_page_error: on_error_hint = None,
                                     keep_original_order: bool = False,
                                     load_html: bool = False,
                                     ) -> AsyncGenerator[ScrapeResult, None]:

        page_urls = [f"https://www.xvideos.com/history/{page}" for page in range(pages)]
        videos_concurrency = videos_concurrency or self.core.configuration.videos_concurrency
        pages_concurrency = pages_concurrency or self.core.configuration.pages_concurrency
        assert videos_concurrency and pages_concurrency

        async for video in self.helper.iterator(target_page_urls=page_urls, video_link_extractor=extractor_account,
                                         max_video_concurrency=videos_concurrency,
                                         max_page_concurrency=pages_concurrency,
                                         page_request_method="POST",
                                         on_video_error=on_video_error,
                                         on_page_error=on_page_error,
                                         fetch_html=load_html,
                                         keep_original_order=keep_original_order):

            yield video

    async def get_liked_videos(self, pages: int = 2, videos_concurrency: int | None = None,
                                     pages_concurrency: int | None = None,
                               on_video_error: on_error_hint = on_error,
                               on_page_error: on_error_hint = None,
                               keep_original_order: bool = False,
                                load_html: bool = False,
                               ) -> AsyncGenerator[ScrapeResult, None]:

        page_urls = [f"https://www.xvideos.com/videos-i-like/{page}" for page in range(pages)]
        videos_concurrency = videos_concurrency or self.core.configuration.videos_concurrency
        pages_concurrency = pages_concurrency or self.core.configuration.pages_concurrency
        assert videos_concurrency and pages_concurrency
        async for video in self.helper.iterator(target_page_urls=page_urls, video_link_extractor=extractor_account,
                                         max_video_concurrency=videos_concurrency,
                                         max_page_concurrency=pages_concurrency,
                                         page_request_method="POST",
                                         on_video_error=on_video_error,
                                         on_page_error=on_page_error,
                                         fetch_html=load_html,
                                         keep_original_order=keep_original_order):

            yield video

    async def get_watch_later_videos(self, pages: int = 2, videos_concurrency: int | None = None,
                                     pages_concurrency: int | None = None,
                                     on_video_error: on_error_hint = on_error,
                                     on_page_error: on_error_hint = None,
                                     keep_original_order: bool = False,
                                     load_html: bool = False,
                                     ) -> AsyncGenerator[ScrapeResult, None]:

        page_urls = [f"https://www.xvideos.com/watch-later/{page}" for page in range(pages)]
        videos_concurrency = videos_concurrency or self.core.configuration.videos_concurrency
        pages_concurrency = pages_concurrency or self.core.configuration.pages_concurrency
        assert videos_concurrency and pages_concurrency
        async for video in self.helper.iterator(target_page_urls=page_urls, video_link_extractor=extractor_account,
                                         max_video_concurrency=videos_concurrency,
                                         max_page_concurrency=pages_concurrency,
                                         page_request_method="POST",
                                         on_video_error=on_video_error,
                                         fetch_html=load_html,
                                         on_page_error=on_page_error,
                                         keep_original_order=keep_original_order):

            yield video


@dataclass(slots=True, kw_only=True)
class Video(BaseMedia):
    url: str
    core: BaseCore
    title: str | None = None
    description: str | None = None
    thumbnail_url: str | None = None
    preview_video_url: str | None = None
    publish_date: str | None = None
    content_url: str | None = None
    tags: list | None = None
    views: str | None = None
    likes: str | None = None
    dislikes: str | None = None
    rating_votes: str | None = None
    comment_count: str | None = None
    author_link: str | None = None
    length: str | None = None
    pornstars_urls: list | None = None
    embed_url: str | None = None
    cdn_url: str | None = None
    m3u8_base_url: str | None = None

    # Optional
    video_id: str | None = None

    async def _perform_load(self, api: bool, html: bool, anything_else: bool):
        if html:
            await asyncio.gather(self._fetch_html())

    async def _fetch_html(self):
        html_content = await get_html_content(core=self.core, url=self.url)
        assert isinstance(html_content, str)
        data: dict = await asyncio.to_thread(self._extract_html, html_content)

        allowed_fields = {f.name for f in fields(self)}
        # Map shared data
        for key, value in data.items():
            if key in allowed_fields:
                setattr(self, key, value)

    @staticmethod
    def _extract_html(html_content: str) -> dict:
        parser = LexborHTMLParser(html_content)

        data = {}
        for s in parser.css('script[type="application/ld+json"]'):
            if not s.text():
                continue
            try:
                data.update(json.loads(s.text()))
            except Exception:
                continue

        title = html.unescape(data.get("name"))
        description = data.get("description")
        thumbnail_url = (data.get("thumbnailUrl") or [None])[0] if isinstance(data.get("thumbnailUrl"), list) else data.get("thumbnailUrl")
        publish_date = data.get("uploadDate")
        content_url = data.get("contentUrl")
        m3u8_base_url = REGEX_VIDEO_M3U8.search(html_content).group(1)
        thumb = html.unescape(data.get("thumbnailUrl"))[0]
        base_url = re.sub(r'/thumbs(169)?(xnxx)?(l*|poster)/', '/videopreview/', thumb[:thumb.rfind("/")])
        suffix = re.search(r'-(\d+)', base_url)
        base_url = re.sub(r'-(\d+)', '', base_url) if suffix else base_url
        preview_video_url = f"{base_url}_169{suffix.group(0) if suffix else ''}.mp4"
        elements = parser.css("a.is-keyword.btn.btn-default")
        tags = [tag.text() for tag in elements]
        views = parser.css_first("span.icon-f.icf-eye").next.text(strip=True)
        likes = parser.css_first("span.rating-good-nbr").text(strip=True)
        dislikes = parser.css_first("span.rating-bad-nbr").text(strip=True)
        rating_votes = parser.css_first("span.rating-total-txt").text(strip=True)
        comment_count = parser.css_first("button.comments.tab-button").next.next.text(strip=True)
        embed_url = REGEX_IFRAME.search(html.unescape(html_content)).group(1)
        length = parser.css_first("span.duration").text(strip=True)

        try:
            link = parser.css_first("li.main-uploader").css_first('a').attributes.get("href")
            assert isinstance(link, str)
            if not link.startswith("/profiles"):
                author_link = f"https://xvideos.com/channels"

            else:
                author_link = f"https://xvideos.com{link}"

        except AttributeError:
            author_link = None


        _pornstars = parser.css('li.model')
        pornstars = []
        for pornstar in _pornstars:
            pornstars.append(f"https://xvideos.com{pornstar.next.attributes.get('href')}")

        return {
            "title": title,
            "description": description,
            "thumbnail_url": thumbnail_url,
            "publish_date": publish_date,
            "content_url": content_url,
            "m3u8_base_url": m3u8_base_url,
            "preview_video_url": preview_video_url,
            "tags": tags,
            "views": views,
            "likes": likes,
            "dislikes": dislikes,
            "rating_votes": rating_votes,
            "comment_count": comment_count,
            "embed_url": embed_url,
            "length": length,
            "author_link": author_link,
            "pornstars_urls": pornstars,
        }

    async def download(self, configuration: DownloadConfigHLS) -> bool | DownloadReport:
        """
        :param configuration:
        :return:
        """
        config = configuration
        if not config.no_title:
            config.path = os.path.join(config.path, f"{self.title}.mp4")

        config.m3u8_base_url = self.m3u8_base_url

        try:
            logger.info(f"Downloading video: {self.title}")
            return await self.core.download(configuration=config)

        except Exception as e: 
            logger.error(f"Failed to download video {self.title}: {e}")
            raise DownloadFailed(str(e))

    @property
    async def get_author(self, load_html: bool = True) -> Channel | None:
        url = self.author_link

        if url:
            channel = Channel(url=url, core=self.core)
            return await channel.load(html=load_html)

        return None

    @property
    async def get_pornstars(self, load_html: bool = True) -> AsyncGenerator[Pornstar, None]:
        for url in self.pornstars_urls:
            star = Pornstar(url=url, core=self.core)
            yield await star.load(html=load_html)



@dataclass(kw_only=True, slots=True)
class BaseChannelPornstar(BaseMedia):
    url: str
    core: BaseCore
    name: str | None = None
    thumbnail_url: str | None = None
    total_videos: int | None = None
    per_page: int | None = None
    total_pages: int | None = None
    profile_hits: str | None = None
    subscribers: str | None = None
    total_videos_views: str | None = None
    signed_up: str | None = None
    last_activity: str | None = None
    worked_for_with_links: list | None = None

    async def _perform_load(self, api: bool, html: bool, anything_else: bool):
        if html:
            await asyncio.gather(self._fetch_html())

    async def _fetch_html(self):
        self._sanitize_url()

        json_data = asyncio.create_task(get_html_content(url=f"{self.url}/videos/best/0", core=self.core))
        html_content = asyncio.create_task(get_html_content(url=f"{self.url}#_tabAboutMe", core=self.core))

        json_data, html_content = await asyncio.gather(json_data, html_content)

        assert isinstance(json_data, str)
        assert isinstance(html_content, str)
        data: dict = await asyncio.to_thread(self._extract_data, html_content=html_content, base_content=json_data)

        allowed_fields = {f.name for f in fields(self)}
        # Map shared data
        for key, value in data.items():
            if key in allowed_fields:
                setattr(self, key, value)

    def _sanitize_url(self):
        ...


    @staticmethod
    def _extract_data(html_content: str, base_content: str):
        json_data = json.loads(base_content)
        parser = LexborHTMLParser(html_content)

        name = parser.css_first('h2 strong.text-danger').text()
        thumbnail_url = parser.css_first('div.profile-pic img').attributes.get('src')
        total_videos = int(json_data["nb_videos"])
        per_page = int(json_data["nb_per_page"])
        total_pages = math.ceil(total_videos / per_page)
        profile_hits = parser.css_first('#pinfo-profile-hits span').text(strip=True)
        subscribers = parser.css_first('#pinfo-subscribers span').text(strip=True)
        try:
            total_video_views = parser.css_first('#pinfo-videos-views span').text(strip=True)

        except:
            paragraphs = parser.css('#pfinfo-col-col1 p')
            # Assuming 'Total Videoaufrufe' is always the 5th <p> tag (index 4)
            if len(paragraphs) > 4:
                total_video_views = paragraphs[4].css_first('span').text(strip=True)

        signed_up = parser.css_first('#pinfo-signedup span').text(strip=True)
        try:
            last_activity = parser.css_first('#pinfo-lastactivity span').text(strip=True)
        except:
            last_activity = None # Can be None sometimes, because it's not always available on the page lol

        names = parser.css('#pinfo-workedfor a')
        worked_for_with_links = [a.attributes.get('href') for a in names if a.attributes.get('href')]

        return {
            "name": name,
            "thumbnail_url": thumbnail_url,
            "total_videos": total_videos,
            "per_page": per_page,
            "total_pages": total_pages,
            "profile_hits": profile_hits,
            "subscribers": subscribers,
            "total_videos_views": total_video_views,
            "signed_up": signed_up,
            "last_activity": last_activity,
            "worked_for_with_links": worked_for_with_links,
        }

    async def worked_for_with(self, load_html: bool = True) -> list[Channel]:
        links_corrected = []

        for link in self.worked_for_with_links:
            if not "profile" in link:
                links_corrected.append(f"https://xvideos.com/channels{link}")

            else:
                links_corrected.append(f"https://xvideos.com{link}")

        channels = [asyncio.create_task(Channel(core=self.core, url=url).load(html=load_html)) for url in links_corrected]
        channels = await asyncio.gather(*channels)
        return channels

    async def videos(self, pages: int = 0, videos_concurrency: int | None = None, pages_concurrency: int | None = None,
                     on_video_error: on_error_hint = on_error,
                     on_page_error: on_error_hint = None,
                     keep_original_order: bool = False
                     ) -> AsyncGenerator[ScrapeResult, None]:
        if pages > self.total_pages:
            pages = self.total_pages

        if pages == 0:
            pages = self.total_pages

        helper = Helper(core=self.core, constructor=Video)
        page_urls = [f"{self.url}/videos/best/{i}" for i in range(pages)] # Don't exceed total available pages
        videos_concurrency = videos_concurrency or self.core.configuration.videos_concurrency
        pages_concurrency = pages_concurrency or self.core.configuration.pages_concurrency
        assert videos_concurrency and pages_concurrency
        async for scrape_result in helper.iterator(target_page_urls=page_urls, video_link_extractor=extractor_account,
                                         max_video_concurrency=videos_concurrency,
                                         max_page_concurrency=pages_concurrency, on_page_error=on_page_error,
                                         on_video_error=on_video_error, keep_original_order=keep_original_order):

            yield scrape_result


@dataclass(kw_only=True, slots=True)
class Channel(BaseChannelPornstar):
    url: str
    core: BaseCore

    def _sanitize_url(self):
        if "/channels/" not in self.url and "profiles" not in self.url:
            self.url = self.url.replace("xvideos.com/", "xvideos.com/channels/")


@dataclass(kw_only=True, slots=True)
class Pornstar(BaseChannelPornstar):
    gender: str | None = None
    age: str | None = None
    video_tags: str | None = None

    @staticmethod
    def _extract_data(html_content: str, base_content: str) -> dict:
        data = BaseChannelPornstar._extract_data(html_content, base_content)
        parser = LexborHTMLParser(html_content)
        data["gender"] = parser.css_first('#pinfo-sex span').text(strip=True)
        try:
            data["age"] = parser.css_first('#pinfo-age span').text(strip=True)
        except:
            data["age"] = None

        data["video_tags"] = parser.css_first('#pinfo-video-tags span').text(strip=True)
        return data


class Client:
    def __init__(self, core: BaseCore = BaseCore()):
        self.core = core
        self.core.initialize_session()
        self.helper = Helper(core=self.core, constructor=Video)
        logger.info("Client initialized")

    async def get_video(self, url: str, load_html: bool = True) -> Video:
        """
        :param url: (str) The video URL
        :param load_html: (bool) Whether or not to load the html page
        :return: (Video) The video object
        """
        video = Video(url=url, core=self.core)
        return await video.load(html=load_html)

    async def search(self, query: str, sorting_sort: str | Sort = Sort.Sort_relevance,
               sorting_date: str | SortDate = SortDate.Sort_all,
               sorting_time: str | SortVideoTime = SortVideoTime.Sort_all,
               sort_quality: str | SortQuality = SortQuality.Sort_all,
               pages: int | str = "all", videos_concurrency: int | None = None,
               load_html: bool = False,
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
        async for scrape_result in self.helper.iterator(target_page_urls=page_urls, video_link_extractor=extractor_account,
                                         max_video_concurrency=videos_concurrency,
                                         max_page_concurrency=pages_concurrency,
                                         on_video_error=on_video_error, keep_original_order=keep_original_order,
                                         on_page_error=on_page_error, fetch_html=load_html,
                                         ):

            yield scrape_result

    async def get_playlist(self, url: str, pages: int = 2, videos_concurrency: int | None = None,
                     pages_concurrency: int | None = None,
                     on_video_error: on_error_hint = on_error,
                     on_page_error: on_error_hint = None,
                     keep_original_order: bool = False,
                     load_html: bool = False) -> AsyncGenerator[ScrapeResult, None]:
        page_urls = [f"{url}/{page}" for page in range(pages)]
        videos_concurrency = videos_concurrency or self.core.configuration.videos_concurrency
        pages_concurrency = pages_concurrency or self.core.configuration.pages_concurrency
        assert videos_concurrency and pages_concurrency

        async for scrape_result in self.helper.iterator(target_page_urls=page_urls, video_link_extractor=extractor_account,
                                         max_video_concurrency=videos_concurrency,
                                         max_page_concurrency=pages_concurrency, fetch_html=load_html,
                                         on_video_error=on_video_error, on_page_error=on_page_error,
                                         keep_original_order=keep_original_order):

            yield scrape_result

    async def get_pornstar(self, url: str, load_html: bool = True) -> Pornstar:
        pornstar = Pornstar(core=self.core, url=url)
        return await pornstar.load(html=load_html)

    async def get_channel(self, url: str, load_html: bool = True) -> Channel:
        channel = Channel(url=url, core=self.core)
        return await channel.load(html=load_html)

    def get_account(self, cookies: dict | None = None) -> Account:
        if cookies:
            account = Account(core=self.core, cookies=cookies)
        else:
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
        await video.download(configuration=config)

    if args.file:
        videos = []
        client = Client()

        with open(args.file, "r") as file:
            content = file.read().splitlines()

        for url in content:
            videos.append(await client.get_video(url))

        for video in videos:
            await video.download(configuration=config)


if __name__ == "__main__":
    asyncio.run(run_main())