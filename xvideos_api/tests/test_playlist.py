import pytest
from ..api import Client


@pytest.mark.asyncio
async def test_playlist():
    client = Client()
    idx = 0
    async for result in client.get_playlist("https://de.xvideos.com/favorite/89127817/playlist_3"):
        idx += 1
        assert isinstance(result.video.title, str)

        if idx <= 30:
            break
