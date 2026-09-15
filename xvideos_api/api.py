from __future__ import annotations
import re
import math
import json
import html
import asyncio
import argparse

from xvideos_api.modules import errors as provider_errors
from base_api.modules.provider import fetch_content, download_errors, download_hls
from base_api.modules.logger import configure_app_logging, get_logger
import logging
from typing import AsyncGenerator, ClassVar
from dataclasses import dataclass
from selectolax.lexbor import LexborHTMLParser
from curl_cffi.requests import AsyncSession
from base_api.modules.type_hints import DownloadReport
from base_api.modules.config import IteratorConfig
from base_api.modules.static_functions import str_to_bool
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from base_api import (
    BaseCore,
    BaseMedia,
    DownloadConfigHLS,
    ErrorAction,
    ErrorMode,
    Helper,
    MediaLoadError,
    MediaLoadErrors,
    RetryPolicy,
    ScrapeErrorContext,
    ScrapeResult,
    media_field,
    make_iterator_config,
    is_resource_gone,
    default_on_error,
    scrape_stream,
)

from xvideos_api.modules.errors import (NotFound, NetworkError, UnknownNetworkError, BotDetection,
                                        ProxyError, DownloadFailed, NoLoginCookies)
from xvideos_api.modules.consts import (cookies, headers, extractor_account, REGEX_VIDEO_M3U8, REGEX_IFRAME)
from xvideos_api.modules.sorting import Sort, SortVideoTime, SortQuality, SortDate


logger = get_logger(__name__)


HELPER_RETRY = RetryPolicy(max_attempts=4, base_delay=0.5, max_delay=8.0)

_is_resource_gone = is_resource_gone
on_error = default_on_error


async def get_html_content(core: BaseCore, url: str, *, owner=None) -> str:
    return await fetch_content(core, url, logger=logger, owner=owner,
                               error_types=provider_errors)


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


    def get_recommended_videos(
        self,
        pages: int = 2,
        iterator_config: IteratorConfig | None = None,
    ) -> AsyncGenerator[ScrapeResult[Video], None]:

        page_urls = [f"https://www.xvideos.com/history/{page}" for page in range(pages)]
        if iterator_config is None:
            iterator_config = make_iterator_config(page_request_method="POST")

        return scrape_stream(
            core=self.core,
            constructor=Video,
            target_page_urls=page_urls,
            item_extractor=extractor_account,
            iterator_config=iterator_config,
        )

    def get_liked_videos(
        self,
        pages: int = 2,
        iterator_config: IteratorConfig | None = None,
    ) -> AsyncGenerator[ScrapeResult[Video], None]:

        page_urls = [f"https://www.xvideos.com/videos-i-like/{page}" for page in range(pages)]
        if iterator_config is None:
            iterator_config = make_iterator_config(page_request_method="POST")

        return scrape_stream(
            core=self.core,
            constructor=Video,
            target_page_urls=page_urls,
            item_extractor=extractor_account,
            iterator_config=iterator_config,
        )

    def get_watch_later_videos(
        self,
        pages: int = 2,
        iterator_config: IteratorConfig | None = None,
    ) -> AsyncGenerator[ScrapeResult[Video], None]:

        page_urls = [f"https://www.xvideos.com/watch-later/{page}" for page in range(pages)]
        if iterator_config is None:
            iterator_config = make_iterator_config(page_request_method="POST")

        return scrape_stream(
            core=self.core,
            constructor=Video,
            target_page_urls=page_urls,
            item_extractor=extractor_account,
            iterator_config=iterator_config,
        )


@dataclass(slots=True, kw_only=True)
class Video(BaseMedia):
    url: str
    core: BaseCore
    title: str | None = media_field("html")
    description: str | None = media_field("html")
    thumbnail_url: str | None = media_field("html")
    preview_video_url: str | None = media_field("html")
    publish_date: str | None = media_field("html")
    content_url: str | None = media_field("html")
    tags: list | None = media_field("html")
    views: str | None = media_field("html")
    likes: str | None = media_field("html")
    dislikes: str | None = media_field("html")
    rating_votes: str | None = media_field("html")
    comment_count: str | None = media_field("html")
    author_link: str | None = media_field("html")
    length: str | None = media_field("html")
    pornstars_urls: list | None = media_field("html")
    embed_url: str | None = media_field("html")
    cdn_url: str | None = None
    m3u8_base_url: str | None = media_field("html")

    # Optional
    video_id: str | None = None

    loader_methods: ClassVar[dict[str, str]] = {"html": "_load_html"}

    async def _load_html(self) -> dict[str, object]:
        html_content = await get_html_content(core=self.core, url=self.url, owner=self)
        return await asyncio.to_thread(self._extract_html, html_content, self.url)

    @staticmethod
    def _extract_html(html_content: str, url: str | None = None) -> dict:
        parser = LexborHTMLParser(html_content)

        data = {}
        for s in parser.css('script[type="application/ld+json"]'):
            if not s.text():
                continue
            try:
                data.update(json.loads(s.text()))
            except (TypeError, ValueError):
                logger.warning("Skipping invalid JSON-LD metadata for %s", url, exc_info=True)
                continue

        # Title
        title = None
        if raw_title := data.get("name"):
            title = html.unescape(raw_title)
        elif match := re.search(r"html5player\.setVideoTitle\('([^']+)'\)", html_content):
            title = html.unescape(match.group(1))
        elif title_node := parser.css_first("#title-auto-tr, .page-title, .video-title"):
            title = title_node.text(strip=True)

        # Description
        description = html.unescape(data["description"]) if data.get("description") else None
        if not description:
            if meta := parser.css_first('meta[name="description"], meta[property="og:description"]'):
                description = meta.attributes.get("content")
        if not description:
            description = title

        # Thumbnail URL
        raw_thumb = data.get("thumbnailUrl")
        thumbnail_url = None
        if isinstance(raw_thumb, list) and raw_thumb:
            thumbnail_url = raw_thumb[0]
        elif isinstance(raw_thumb, str):
            thumbnail_url = raw_thumb
        elif match := re.search(r"html5player\.setThumbUrl\('([^']+)'\)", html_content):
            thumbnail_url = match.group(1)
        elif match := re.search(r"html5player\.setThumbUrl169\('([^']+)'\)", html_content):
            thumbnail_url = match.group(1)
        elif img_node := parser.css_first(".video-pic img"):
            thumbnail_url = img_node.attributes.get("src")

        # Preview video URL
        preview_video_url = f"{thumbnail_url.rsplit('/', 1)[0]}/preview.mp4" if thumbnail_url else None

        # Publish date
        publish_date = data.get("uploadDate")
        if not publish_date:
            if match := re.search(r"<!--\s*dispo\s*-\s*([A-Za-z]+,\s*\d+\s+[A-Za-z]+\s+\d+\s+\d+:\d+:\d+\s+[+\-]?\d*)", html_content):
                publish_date = match.group(1)

        # Content URL
        content_url = data.get("contentUrl")
        if not content_url:
            if match := (
                re.search(r"html5player\.setVideoUrlHigh\('([^']+)'\)", html_content)
                or re.search(r"html5player\.setVideoUrlLow\('([^']+)'\)", html_content)
            ):
                content_url = match.group(1)

        # HLS master playlist URL
        m = REGEX_VIDEO_M3U8.search(html_content) or re.search(r"html5player\.setVideoHLS\('([^']+)'\)", html_content)
        m3u8_base_url = m.group(1) if m else None

        # Tags
        tags = [tag.text(strip=True) for tag in parser.css("a.is-keyword") if tag.text(strip=True)]

        # Views
        views_node = parser.css_first("#v-views strong.mobile-hide, #v-views strong")
        views = views_node.text(strip=True) if views_node else None
        if not views and (eye := parser.css_first("span.icon-f.icf-eye")):
            views = eye.parent.text(strip=True) if eye.parent else None

        # Likes, dislikes, rating votes
        likes_node = parser.css_first("span.rating-good-nbr")
        likes = likes_node.text(strip=True) if likes_node else "0"

        dislikes_node = parser.css_first("span.rating-bad-nbr")
        dislikes = dislikes_node.text(strip=True) if dislikes_node else "0"

        rating_votes_node = parser.css_first("span.rating-total-txt")
        rating_votes = rating_votes_node.text(strip=True) if rating_votes_node else "0"

        # Comment count
        comment_node = parser.css_first("button.comments .badge, .thread-node-children-count.badge")
        comment_count = comment_node.text(strip=True) if comment_node else "0"

        # Embed URL
        embed_node = parser.css_first("#copy-video-embed")
        if embed_node and (raw_embed := embed_node.attributes.get("value")):
            embed_url = raw_embed
        elif match := (REGEX_IFRAME.search(html_content) or re.search(r'id=["\']copy-video-embed["\'][^>]*value=["\']([^"\']+)["\']', html_content)):
            embed_url = html.unescape(match.group(1))
        elif match := re.search(r"html5player\.setEncodedIdVideo\('([^']+)'\)", html_content):
            embed_url = f'<iframe src="https://www.xvideos.com/embedframe/{match.group(1)}" frameborder=0 width=510 height=400 scrolling=no allowfullscreen=allowfullscreen></iframe>'
        else:
            embed_url = None

        # Duration / length
        length_node = parser.css_first("span.duration")
        length = length_node.text(strip=True) if length_node else None

        # Author link
        author_link = None
        uploader_node = parser.css_first("li.main-uploader a")
        if uploader_node and (href := uploader_node.attributes.get("href")):
            author_link = href if href.startswith("http") else f"https://xvideos.com{href}"
        elif match := re.search(r"html5player\.setUploaderName\('([^']+)'\)", html_content):
            author_link = f"https://xvideos.com/{match.group(1)}"

        # Featured pornstars
        pornstars_urls = []
        for el in parser.css("li.model a[href]"):
            href = el.attributes.get("href")
            if href:
                pornstars_urls.append(href if href.startswith("http") else f"https://xvideos.com{href}")

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
            "pornstars_urls": pornstars_urls,
        }

    @download_errors(DownloadFailed)
    async def download(self, configuration: DownloadConfigHLS) -> bool | DownloadReport:
        return await download_hls(self, configuration)

    @property
    async def get_author(self, load_html: bool = True) -> Channel | None:
        url = await self.get_field("author_link")

        if url:
            channel = Channel(url=url, core=self.core)
            if load_html:
                await channel.load_sources("html")
            return channel

        return None

    @property
    async def get_pornstars(self, load_html: bool = True) -> AsyncGenerator[Pornstar, None]:
        pornstars_urls = await self.get_field("pornstars_urls")
        for url in pornstars_urls:
            star = Pornstar(url=url, core=self.core)
            if load_html:
                await star.load_sources("html")
            yield star



@dataclass(kw_only=True, slots=True)
class BaseChannelPornstar(BaseMedia):
    url: str
    core: BaseCore
    name: str | None = media_field("html")
    thumbnail_url: str | None = media_field("html")
    total_videos: int | None = media_field("html")
    per_page: int | None = media_field("html")
    total_pages: int | None = media_field("html")
    profile_hits: str | None = media_field("html")
    subscribers: str | None = media_field("html")
    total_videos_views: str | None = media_field("html")
    signed_up: str | None = media_field("html")
    last_activity: str | None = media_field("html")
    worked_for_with_links: list | None = media_field("html")

    loader_methods: ClassVar[dict[str, str]] = {"html": "_load_html"}

    async def _load_html(self) -> dict[str, object]:
        self.url = self.url.split("#")[0].rstrip("/")
        self._sanitize_url()

        json_data = asyncio.create_task(get_html_content(url=f"{self.url}/videos/best/0", core=self.core, owner=self))
        html_content = asyncio.create_task(get_html_content(url=f"{self.url}#_tabAboutMe", core=self.core, owner=self))

        json_data, html_content = await asyncio.gather(json_data, html_content)

        return await asyncio.to_thread(
            self._extract_data,
            html_content=html_content,
            base_content=json_data,
        )

    def _sanitize_url(self):
        ...

    @staticmethod
    def _extract_data(html_content: str, base_content: str, parser: LexborHTMLParser | None = None) -> dict[str, object]:
        if parser is None:
            parser = LexborHTMLParser(html_content)

        name_node = parser.css_first("h2 strong.text-danger") or parser.css_first("h2 strong")
        name = name_node.text(strip=True) if name_node else None

        img_node = parser.css_first("div.profile-pic img") or parser.css_first(".profile-pic img")
        thumbnail_url = img_node.attributes.get("src") if img_node else None

        total_videos = None
        per_page = None
        total_pages = None
        if base_content:
            try:
                json_data = json.loads(base_content)
                if "nb_videos" in json_data:
                    total_videos = int(json_data["nb_videos"])
                if "nb_per_page" in json_data:
                    per_page = int(json_data["nb_per_page"])
                if total_videos is not None and per_page:
                    total_pages = math.ceil(total_videos / per_page)
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

        if total_videos is None:
            count_node = parser.css_first("#tab-videos span.count")
            if count_node:
                raw_count = count_node.text(strip=True).replace(".", "").replace(",", "")
                try:
                    total_videos = int(raw_count)
                    per_page = 24
                    total_pages = math.ceil(total_videos / per_page)
                except ValueError:
                    pass

        profile_hits_node = parser.css_first("#pinfo-profile-hits span")
        profile_hits = profile_hits_node.text(strip=True) if profile_hits_node else None

        subs_node = parser.css_first("#pinfo-subscribers span") or parser.css_first(".user-subscribe .count")
        subscribers = subs_node.text(strip=True) if subs_node else None

        views_node = parser.css_first("#pinfo-videos-views span") or parser.css_first("h2 small.mobile-only-hide span.mobile-hide")
        total_videos_views = views_node.text(strip=True) if views_node else None

        signed_node = parser.css_first("#pinfo-signedup span")
        signed_up = signed_node.text(strip=True) if signed_node else None

        act_node = parser.css_first("#pinfo-lastactivity span")
        last_activity = act_node.text(strip=True) if act_node else None

        worked_for_with_links = [
            a.attributes.get("href")
            for a in parser.css("#pinfo-workedfor a[href]")
            if a.attributes.get("href")
        ]

        return {
            "name": name,
            "thumbnail_url": thumbnail_url,
            "total_videos": total_videos,
            "per_page": per_page,
            "total_pages": total_pages,
            "profile_hits": profile_hits,
            "subscribers": subscribers,
            "total_videos_views": total_videos_views,
            "signed_up": signed_up,
            "last_activity": last_activity,
            "worked_for_with_links": worked_for_with_links,
        }

    async def worked_for_with(self, load_html: bool = True) -> list[Channel]:
        await self.load_fields("worked_for_with_links")
        links_corrected = []

        for link in self.worked_for_with_links or []:
            if link.startswith("http"):
                links_corrected.append(link)
            elif link.startswith("/profiles") or link.startswith("/channels"):
                links_corrected.append(f"https://xvideos.com{link}")
            else:
                links_corrected.append(f"https://xvideos.com/channels{link}")

        channels = [Channel(core=self.core, url=url) for url in links_corrected]
        if load_html:
            await asyncio.gather(*(channel.load_sources("html") for channel in channels))
        return channels

    async def videos(
        self,
        pages: int = 0,
        iterator_config: IteratorConfig | None = None,
    ) -> AsyncGenerator[ScrapeResult[Video], None]:
        total_pages = await self.get_field("total_pages")
        if pages > total_pages:
            pages = total_pages

        if pages == 0:
            pages = total_pages
        url = self.url
        page_urls = [f"{url}/videos/best/{i}" for i in range(pages)] # Don't exceed total available pages
        if iterator_config is None:
            iterator_config = make_iterator_config()

        stream = scrape_stream(
            core=self.core,
            constructor=Video,
            target_page_urls=page_urls,
            item_extractor=extractor_account,
            iterator_config=iterator_config,
        )
        async for scrape_result in stream:
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
    gender: str | None = media_field("html")
    age: str | None = media_field("html")
    video_tags: str | None = media_field("html")

    def _sanitize_url(self):
        if "/pornstars/" not in self.url and "profiles" not in self.url:
            self.url = self.url.replace("xvideos.com/", "xvideos.com/pornstars/")

    @staticmethod
    def _extract_data(html_content: str, base_content: str, parser: LexborHTMLParser | None = None) -> dict:
        if parser is None:
            parser = LexborHTMLParser(html_content)
        data = BaseChannelPornstar._extract_data(html_content, base_content, parser=parser)

        sex_node = parser.css_first("#pinfo-sex span")
        data["gender"] = sex_node.text(strip=True) if sex_node else None

        age_node = parser.css_first("#pinfo-age span")
        if age_node:
            data["age"] = age_node.text(strip=True)
        else:
            header_small = parser.css_first("h2 small.mobile-hide")
            if header_small and (match := re.search(r"\b(\d{1,2})\s*(?:y\b|yo\b|years?\b|jahre\b)", header_small.text(), re.IGNORECASE)):
                data["age"] = match.group(1)
            else:
                data["age"] = None

        tags_node = parser.css_first("#pinfo-video-tags span")
        data["video_tags"] = tags_node.text(strip=True) if tags_node else None
        return data


class Client:
    def __init__(self, core: BaseCore | None = None):
        if core is None:
            core = BaseCore()
        self.core = core
        self.account = None
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
        if load_html:
            await video.load_sources("html")
        return video

    def search(self, query: str, sorting_sort: str | Sort = Sort.Sort_relevance,
               sorting_date: str | SortDate = SortDate.Sort_all,
               sorting_time: str | SortVideoTime = SortVideoTime.Sort_all,
               sort_quality: str | SortQuality = SortQuality.Sort_all,
               pages: int | str = "all",
               iterator_config: IteratorConfig | None = None,
                      ) -> AsyncGenerator[ScrapeResult[Video], None]:


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

        if iterator_config is None:
            iterator_config = make_iterator_config()

        return scrape_stream(
            core=self.core,
            constructor=Video,
            target_page_urls=page_urls,
            item_extractor=extractor_account,
            iterator_config=iterator_config,
        )

    def get_playlist(
        self,
        url: str,
        pages: int = 2,
        iterator_config: IteratorConfig | None = None,
    ) -> AsyncGenerator[ScrapeResult[Video], None]:
        page_urls = [f"{url}/{page}" for page in range(pages)]
        if iterator_config is None:
            iterator_config = make_iterator_config()

        return scrape_stream(
            core=self.core,
            constructor=Video,
            target_page_urls=page_urls,
            item_extractor=extractor_account,
            iterator_config=iterator_config,
        )

    async def get_pornstar(self, url: str, load_html: bool = True) -> Pornstar:
        pornstar = Pornstar(core=self.core, url=url)
        if load_html:
            await pornstar.load_sources("html")
        return pornstar

    async def get_channel(self, url: str, load_html: bool = True) -> Channel:
        channel = Channel(url=url, core=self.core)
        if load_html:
            await channel.load_sources("html")
        return channel

    def get_account(self, cookies: dict | None = None) -> Account:
        if cookies:
            self.account = Account(core=self.core, cookies=cookies)
        else:
            self.account = Account(core=self.core)

        return self.account


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="XVideos API Command Line Interface")
    parser.add_argument("--download", metavar="URL", type=str, help="URL to download from")
    parser.add_argument("--quality", metavar="best|half|worst", type=str, default="best", help="The video quality (best, half, worst)")
    parser.add_argument("--file", metavar="FILE", type=str, help="(Optional) Specify a file with URLs (separated with new lines)")
    parser.add_argument("--output", metavar="DIR", type=str, required=True, help="The output path (with filename or directory)")
    parser.add_argument("--no-title", metavar="True,False", type=str, nargs="?", const="True", default="False",
                        help="Whether to apply video title automatically to output path or not")
    return parser


async def run_main(args_list: list[str] | None = None):
    parser = create_parser()
    args = parser.parse_args(args_list)
    no_title = str_to_bool(args.no_title) if isinstance(args.no_title, str) else bool(args.no_title)
    config = DownloadConfigHLS(
        quality=args.quality,
        path=args.output,
        no_title=no_title
    )

    urls: list[str] = []
    if args.download:
        urls.append(args.download)
    if args.file:
        with open(args.file, "r") as file:
            urls.extend([line.strip() for line in file.readlines() if line.strip()])

    if not urls:
        parser.print_help()
        return

    client = Client()
    for url in urls:
        print(f"Fetching video information for: {url}")
        try:
            video = await client.get_video(url, load_html=True)
            title = getattr(video, "title", None) or url
            print(f"Starting download for: {title}")
            await video.download(configuration=config)
            print(f"Download complete: {title}")
        except Exception as e:
            logger.exception("CLI failed while processing %s", url)
            print(f"Error downloading {url}: {e}")


def main():
    configure_app_logging(level=logging.INFO)
    try:
        asyncio.run(run_main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")


if __name__ == "__main__":
    main()
