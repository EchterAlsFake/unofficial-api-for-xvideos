import pytest
from ..api import Client



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
    async for result in pornstar.videos(videos_concurrency=1, pages_concurrency=1):
        assert isinstance(result.video.title, str) and len(result.video.title) >= 3
        idx += 1
        if idx == 3:
            break
