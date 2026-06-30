import pytest
from ..api import Client


@pytest.mark.asyncio
async def test_channel():
    client = Client()
    channel = await client.get_channel("https://de.xvideos.com/teddy_tarantino")

    assert isinstance(channel.name, str)
    assert isinstance(channel.thumbnail_url, str)
    assert isinstance(channel.total_pages, int)
    assert isinstance(channel.per_page, int)
    assert isinstance(channel.total_videos, int)
    assert isinstance(channel.country, str)
    assert isinstance(channel.profile_hits, str)
    assert isinstance(channel.subscribers, str)
    assert isinstance(channel.signed_up, str)
    assert isinstance(channel.last_activity, str)

    stuff = await channel.worked_for_with()
    assert isinstance(stuff.name, str)

    idx = 0
    async for result in channel.videos():
        idx += 1
        assert isinstance(result.video.title, str)

        if idx >= 3:
            break
