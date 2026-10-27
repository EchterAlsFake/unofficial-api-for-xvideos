"""Dedicated edge case and regression tests for xvideos_api."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from xvideos_api import (
    Client, Video, Channel, Pornstar,
)
from xvideos_api.modules.sorting import (
    Sort, SortDate, SortVideoTime, SortQuality,
)
from xvideos_api.modules.consts import extractor_account, extractor_profile_json, is_next_page
from base_api import is_resource_gone, BaseCore


@pytest.mark.asyncio
async def test_get_author_as_property_and_callable():
    """Video.get_author must work both as a property and as a callable."""
    core = BaseCore()
    video = Video(url="https://www.xvideos.com/video.test/mock", core=core)

    with patch.object(Video, "get_field", AsyncMock(return_value="https://www.xvideos.com/channels/mock_channel")), \
         patch.object(Channel, "load_sources", AsyncMock()) as mock_load:

        # 1. As awaitable property (Porn_Fetch backend style)
        author1 = await video.get_author
        assert isinstance(author1, Channel)
        assert author1.url == "https://www.xvideos.com/channels/mock_channel"
        assert mock_load.call_count == 1

        mock_load.reset_mock()

        # 2. As callable without args (Porn_Fetch CLI / standard style)
        author2 = await video.get_author()
        assert isinstance(author2, Channel)
        assert author2.url == "https://www.xvideos.com/channels/mock_channel"
        assert mock_load.call_count == 1

        mock_load.reset_mock()

        # 3. As callable with load_html=False
        author3 = await video.get_author(load_html=False)
        assert isinstance(author3, Channel)
        assert mock_load.call_count == 0


@pytest.mark.asyncio
async def test_get_pornstars_as_property_and_callable():
    """Video.get_pornstars must work both as an async iterable and as a callable."""
    core = BaseCore()
    video = Video(url="https://www.xvideos.com/video.test/mock", core=core)

    stars_urls = [
        "https://www.xvideos.com/pornstars/star_one",
        "https://www.xvideos.com/pornstars/star_two",
    ]

    with patch.object(Video, "get_field", AsyncMock(return_value=stars_urls)), \
         patch.object(Pornstar, "load_sources", AsyncMock()) as mock_load:

        # 1. Property style async iteration
        yielded1 = []
        async for star in video.get_pornstars:
            assert isinstance(star, Pornstar)
            yielded1.append(star.url)
        assert len(yielded1) == 2
        assert mock_load.call_count == 2

        mock_load.reset_mock()

        # 2. Callable style async iteration
        yielded2 = []
        async for star in video.get_pornstars():
            assert isinstance(star, Pornstar)
            yielded2.append(star.url)
        assert len(yielded2) == 2
        assert mock_load.call_count == 2

        mock_load.reset_mock()

        # 3. Callable with load_html=False
        yielded3 = []
        async for star in video.get_pornstars(load_html=False):
            assert isinstance(star, Pornstar)
            yielded3.append(star.url)
        assert len(yielded3) == 2
        assert mock_load.call_count == 0


def test_extractor_account_duration_not_in_title():
    """Title must not have the duration concatenated to it."""
    html = """
    <div class="frame-block thumb-block">
        <div class="thumb-inside">
            <div class="thumb">
                <a href="/video.12345/awesome_sample_video">
                    <img src="https://assets.xvideos-cdn.com/img/lightbox/lightbox-blank.gif"
                         data-src="https://thumb.xvideos-cdn.com/12345/thumb.jpg"
                         data-videoid="12345">
                </a>
            </div>
        </div>
        <div class="thumb-under">
            <p class="title">
                <a href="/video.12345/awesome_sample_video" title="Awesome Sample Video">
                    Awesome Sample Video<span class="duration">10 min</span>
                </a>
            </p>
            <p class="metadata">
                <span class="bg">
                    <span class="duration">10 min</span>
                    <span> - <span>1.5M Views</span></span>
                </span>
            </p>
        </div>
    </div>
    """
    items = extractor_account(html)
    assert len(items) == 1
    assert items[0]["title"] == "Awesome Sample Video"
    assert items[0]["thumbnail_url"] == "https://thumb.xvideos-cdn.com/12345/thumb.jpg"
    assert items[0]["video_id"] == "12345"
    assert items[0]["views"] == "1.5M"
    assert items[0]["length"] == "10 min"


def test_extractor_account_filters_non_video_anchors_and_profiles():
    """Non-video links (e.g. channel links starting with /video-...) and profile blocks must be skipped."""
    html = """
    <!-- Profile suggestion block in search results -->
    <div id="profile_mia-khalifa" class="thumb-block thumb-block-profile">
        <div class="thumb-inside">
            <div class="thumb"><a href="/mia-khalifa"><img src="thumb.jpg"></a></div>
        </div>
        <div class="thumb-under"><p class="profile-name"><a href="/mia-khalifa">Mia Khalifa</a></p></div>
    </div>

    <!-- Real video block with uploader link named video-something -->
    <div class="frame-block thumb-block">
        <div class="thumb-inside">
            <div class="thumb">
                <a href="/video.abc1234/real_video">
                    <img src="https://thumb.xvideos-cdn.com/abc/thumb.jpg" data-videoid="999">
                </a>
            </div>
        </div>
        <div class="thumb-under">
            <p class="title"><a href="/video.abc1234/real_video">Real Video Title</a></p>
            <p class="metadata"><a href="/video-porno-one">Video Porno One</a></p>
        </div>
    </div>
    """
    items = extractor_account(html)
    assert len(items) == 1
    assert items[0]["url"] == "https://www.xvideos.com/video.abc1234/real_video"
    assert items[0]["title"] == "Real Video Title"


def test_extractor_profile_json_unescapes_entities():
    """JSON profile listing titles containing HTML entities must be unescaped."""
    raw_json = """{
        "videos": [
            {
                "id": 101,
                "u": "/prof-video-click/channels/demo/101/step_sister_s_secret",
                "tf": "Step Sister&#039;s Secret &amp; Desire &quot;Special&quot;",
                "i": "https://thumb.com/101.jpg",
                "d": "15 min",
                "n": 500000
            }
        ]
    }"""
    items = extractor_profile_json(raw_json)
    assert len(items) == 1
    assert items[0]["title"] == "Step Sister's Secret & Desire \"Special\""
    assert items[0]["url"] == "https://www.xvideos.com/video.101/step_sister_s_secret"
    assert items[0]["video_id"] == "101"
    assert items[0]["views"] == "500000"


def test_is_next_page_check():
    """is_next_page must return True only when pagination next link is present."""
    html_with_next = '<div class="pagination"><ul><li><a href="/?k=test&p=1" class="next-page">Next</a></li></ul></div>'
    html_without_next = '<div class="pagination"><ul><li><span class="no-next">End</span></li></ul></div>'
    assert is_next_page(html_with_next) is True
    assert is_next_page(html_without_next) is False


def test_video_extract_html_author_fallback():
    """Video._extract_html must fallback to setUploaderName when li.main-uploader is absent."""
    html = """
    <div id="main">
        <script>
            html5player.setVideoTitle('Fallback Author Test Video');
            html5player.setUploaderName('stealth_creator');
            html5player.setEncodedIdVideo('x123');
        </script>
    </div>
    """
    data = Video._extract_html(html)
    assert data["title"] == "Fallback Author Test Video"
    assert data["author_name"] == "stealth_creator"
    assert data["author_link"] == "https://xvideos.com/stealth_creator"


@pytest.mark.asyncio
async def test_channel_videos_zero_or_none_pages():
    """Channel.videos must gracefully return without exception when total_pages is None or 0."""
    core = BaseCore()
    channel = Channel(url="https://www.xvideos.com/channels/empty_creator", core=core)

    with patch.object(Channel, "get_field", AsyncMock(return_value=None)):
        results = [res async for res in channel.videos(pages=0)]
        assert len(results) == 0

    with patch.object(Channel, "get_field", AsyncMock(return_value=0)):
        results = [res async for res in channel.videos(pages=0)]
        assert len(results) == 0


@pytest.mark.asyncio
async def test_worked_for_with_limit_and_error_tolerance():
    """BaseChannelPornstar.worked_for_with must respect limit and tolerate individual failures."""
    core = BaseCore()
    channel = Channel(url="https://www.xvideos.com/channels/popular_creator", core=core)
    channel.worked_for_with_links = [
        "/channels/good1",
        "/profiles/good2",
        "/models/good3",
        "/channels/bad4",
    ]

    async def mock_load_sources(source, *args, **kwargs):
        if "bad4" in source.url:
            raise RuntimeError("Throttled or 500 error")

    with patch.object(Channel, "load_fields", AsyncMock()):
        # Test limit=2
        res_limited = await channel.worked_for_with(load_html=False, limit=2)
        assert len(res_limited) == 2
        assert res_limited[0].url == "https://xvideos.com/channels/good1"
        assert res_limited[1].url == "https://xvideos.com/profiles/good2"

        # Test error resilience with load_html=True
        with patch.object(Channel, "load_sources", mock_load_sources):
            all_res = await channel.worked_for_with(load_html=True)
            assert len(all_res) == 4


def test_search_url_generation():
    """Client.search must properly encode queries without %2B space mangling and handle page numbers."""
    from xvideos_api import api as api_mod
    client = Client()

    captured_urls = []

    def mock_scrape_stream(**kwargs):
        captured_urls.extend(kwargs.get("target_page_urls", []))
        async def empty_gen():
            if False:
                yield None
        return empty_gen()

    with patch.object(api_mod, "scrape_stream", side_effect=mock_scrape_stream):
        # 1. Multi-word search with 3 pages
        client.search("Mia Khalifa", pages=3)
        assert len(captured_urls) == 3
        # Ensure 'k=Mia+Khalifa' and NOT 'k=Mia%2BKhalifa'
        assert captured_urls[0] == "https://www.xvideos.com/?k=Mia+Khalifa&sort=relevance&datef=all&durf=allduration&quality=all"
        assert captured_urls[1] == "https://www.xvideos.com/?k=Mia+Khalifa&sort=relevance&datef=all&durf=allduration&quality=all&p=1"
        assert captured_urls[2] == "https://www.xvideos.com/?k=Mia+Khalifa&sort=relevance&datef=all&durf=allduration&quality=all&p=2"

        captured_urls.clear()

        # 2. Search with pages="all"
        client.search("Mia Khalifa", pages="all")
        assert len(captured_urls) == 10

        captured_urls.clear()

        # 3. Search with pages=0
        client.search("Mia Khalifa", pages=0)
        assert len(captured_urls) == 0


@pytest.mark.asyncio
async def test_deleted_video_is_resource_gone():
    """Requesting a non-existent video URL must produce an exception recognized by is_resource_gone."""
    client = Client()
    with pytest.raises(Exception) as exc_info:
        await client.get_video("https://www.xvideos.com/video9999999999999/non_existent_test_slug")
    assert is_resource_gone(exc_info.value) is True


@pytest.mark.asyncio
async def test_multiregion_video_parsing():
    """Live test verifying video parsing consistency across regional subdomains."""
    client = Client()
    for domain in ["www", "de"]:
        url = f"https://{domain}.xvideos.com/video.hutebiv136e/mia_khalifa_in_the_shower"
        video = await client.get_video(url)
        assert isinstance(video.title, str) and len(video.title) > 0
        assert isinstance(video.views, str) and len(video.views) > 0
        assert video.author_name == "Mia Khalifa"
        assert video.author_link is not None
