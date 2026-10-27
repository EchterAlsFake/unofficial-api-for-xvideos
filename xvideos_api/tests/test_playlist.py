import pytest
from ..api import Client


@pytest.mark.asyncio
async def test_playlist():
    client = Client()
    idx = 0
    async for result in client.get_playlist("https://de.xvideos.com/favorite/89127817/playlist_3"):
        idx += 1
        video = result.unwrap()
        assert isinstance(video.title, str) and len(video.title) > 0
        assert isinstance(video.url, str) and len(video.url) > 0

        if idx >= 10:
            break

    assert idx > 0, "Playlist returned no videos"
