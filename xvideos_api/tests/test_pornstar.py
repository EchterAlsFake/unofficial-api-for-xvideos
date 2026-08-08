import pytest
from ..api import Client
from base_api.modules.config import IteratorConfig



@pytest.mark.asyncio
async def test_pornstar():
    client = Client()
    pornstar = await client.get_pornstar("https://de.xvideos.com/pornstars/sweetie-fox1")

    assert isinstance(pornstar.total_videos, int)
    assert isinstance(pornstar.total_pages, int)
    assert isinstance(pornstar.name, str) and len(pornstar.name) >= 3
    assert isinstance(pornstar.thumbnail_url, str) and len(pornstar.thumbnail_url) >= 3
    assert isinstance(pornstar.per_page, int)
    assert isinstance(pornstar.gender, str)
    assert isinstance(pornstar.profile_hits, str)
    assert isinstance(pornstar.total_videos_views, str)
    assert isinstance(pornstar.signed_up, str)
    assert isinstance(pornstar.last_activity, (str, type(None)))
    assert isinstance(pornstar.video_tags, str)
    assert isinstance(pornstar.subscribers, str)
    assert isinstance(pornstar.worked_for_with_links, list)

    for channel in await pornstar.worked_for_with():
        assert isinstance(channel.name, str)

    idx = 0
    iterator_config = IteratorConfig(
        max_item_concurrency=1,
        max_page_concurrency=1,
        load_specific_sources=("html",),
    )
    async for result in pornstar.videos(iterator_config=iterator_config):
        video = result.unwrap()
        assert isinstance(video.title, str) and len(video.title) >= 3
        idx += 1
        if idx == 3:
            break
